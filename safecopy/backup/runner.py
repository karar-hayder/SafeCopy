import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from safecopy.backup.dtos import BackupConfig
from safecopy.backup.engine import BackupEngine
from safecopy.backup.verification import verify
from safecopy.db.dtos.backupHistoryDTOs import BackupHistoryCreateDTO
from safecopy.db.dtos.backupVerificationDTOs import BackupVerificationCreateDTO
from safecopy.db.enums import BackupStatus, BackupVerificationStatus, HashType
from safecopy.db.services.backupHistoryService import BackupHistoryService
from safecopy.db.services.backupVerificationService import BackupVerificationService

logger = logging.getLogger("backup_runner")


def run_backup(config: BackupConfig) -> tuple[bool, str]:
    """
    Orchestrate a full backup cycle for a single mapping:
      1. Run the BackupEngine (copy / compress / encrypt)
      2. Record a BackupHistory row via the new DB service
      3. Run verification against the backup
      4. Record a BackupVerification row via the new DB service

    Args:
        config: A BackupConfig describing what to back up and how.

    Returns:
        (success, message) tuple.
    """
    engine = BackupEngine(config)
    history_service = BackupHistoryService()
    verification_service = BackupVerificationService()

    # ------------------------------------------------------------------ #
    # 1. Run the engine
    # ------------------------------------------------------------------ #
    try:
        status, message, duration, size_bytes = engine.run()
        success = status == status.__class__.SUCCESS
    except Exception as e:
        logger.error("BackupEngine.run raised: %s", e, exc_info=True)
        success = False
        message = str(e)
        duration = 0.0
        size_bytes = 0

    backup_path_obj = engine.backup_path_encrypted or engine.backup_path
    backup_path = str(backup_path_obj) if backup_path_obj else None

    # ------------------------------------------------------------------ #
    # 2. Record history
    # ------------------------------------------------------------------ #
    history_uuid = None
    try:
        db_status = BackupStatus.SUCCESS if success else BackupStatus.FAILURE
        history_dto = BackupHistoryCreateDTO(
            user_uuid=config.user_uuid,
            mapping_uuid=config.uuid,
            status=db_status,
            message=message,
            duration=duration,
            size_bytes=size_bytes,
            backup_path=backup_path,
        )
        history_record = history_service.create(history_dto)
        history_uuid = history_record.uuid
        logger.info("Recorded backup history %s", history_uuid)
    except Exception as e:
        logger.error("Failed to record backup history: %s", e)

    # ------------------------------------------------------------------ #
    # 3. Verify the backup (only if the backup succeeded)
    # ------------------------------------------------------------------ #
    if not success:
        return success, message

    verify_status = BackupVerificationStatus.NOT_VERIFIED
    verify_msg = "Verification skipped"
    source_checksum = None
    backup_checksum = None

    try:
        result = verify(config.source, backup_path)
        verify_status = (
            BackupVerificationStatus.SUCCESS
            if result.success
            else BackupVerificationStatus.FAILURE
        )
        verify_msg = result.message
        source_checksum = result.source_checksum
        backup_checksum = result.backup_checksum

        if not result.success:
            logger.warning("Backup verification failed: %s", result.message)
            message += f" (Verification failed: {result.message})"
    except Exception as e:
        logger.error("Verification raised: %s", e)
        verify_status = BackupVerificationStatus.FAILURE
        verify_msg = str(e)

    # ------------------------------------------------------------------ #
    # 4. Record verification result
    # ------------------------------------------------------------------ #
    if history_uuid:
        try:
            verification_dto = BackupVerificationCreateDTO(
                backup_history_uuid=history_uuid,
                checksum_type=HashType.MD5,
                source_checksum=source_checksum,
                backup_checksum=backup_checksum,
                verification_status=verify_status,
                verification_msg=verify_msg,
                verified_at=datetime.now(),
            )
            verification_service.create(verification_dto)
        except Exception as e:
            logger.error("Failed to record verification result: %s", e)

    return success, message


def run_backups_parallel(
    configs: list[BackupConfig],
    max_workers: int = 4,
) -> list[tuple[bool, str]]:
    """
    Run multiple backups in parallel using a thread pool.

    Args:
        configs:     List of BackupConfig objects to run.
        max_workers: Maximum number of concurrent backup threads.

    Returns:
        List of (success, message) tuples in the same order as configs.
    """
    results: list[tuple[bool, str] | None] = [None] * len(configs)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {
            pool.submit(run_backup, config): idx for idx, config in enumerate(configs)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error("Parallel backup error for index %d: %s", idx, e)
                results[idx] = (False, f"Parallel backup error: {e}")

    succeeded = sum(1 for r in results if r and r[0])
    logger.info("Parallel backups done: %d/%d succeeded", succeeded, len(results))
    return results
