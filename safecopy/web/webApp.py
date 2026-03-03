import logging
import os

from flask import Flask
from flask_caching import Cache
from flask_login import LoginManager

from safecopy.scheduler import start_advanced_scheduler
from safecopy.web.middlewares import LoggingMiddleware
from safecopy.web.routes import auth_routes, main_routes


class WebApp:
    def __init__(self, secret_key):
        self.app = Flask(
            __name__,
            template_folder=os.path.join(os.path.dirname(__file__), "templates"),
            static_folder=os.path.join(os.path.dirname(__file__), "static"),
        )
        self.app.config["CACHE_TYPE"] = "simple"
        self.app.config["SECRET_KEY"] = secret_key
        self.cache = Cache(self.app)
        self.login_manager = LoginManager(self.app)
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = "login"
        self.logger = logging.getLogger(__name__)

        from safecopy.db.models import Base
        from safecopy.db.services.userService import UserService
        from safecopy.db.session import engine

        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)

        self.user_service = UserService()

        # Fresh start mechanism
        self.user_service.ensure_admin_exists()

        # Start the scheduler
        start_advanced_scheduler()

        # Setup routes during initialization
        self.setup_routes()

        @self.login_manager.user_loader
        def load_user(user_uuid):
            # Use get_model_by_uuid to return the SQLAlchemy object (required by flask-login)
            return self.user_service.get_model_by_uuid(user_uuid)

    def setup_routes(self):
        # Register main routes
        for route_info in main_routes:
            rule = route_info[0]
            view_func = route_info[1]
            endpoint = route_info[2]
            methods = route_info[3] if len(route_info) > 3 else ["GET"]
            self.app.add_url_rule(rule, endpoint, view_func, methods=methods)

        # Register auth routes
        for route_info in auth_routes:
            rule = route_info[0]
            view_func = route_info[1]
            endpoint = route_info[2]
            methods = route_info[3] if len(route_info) > 3 else ["GET"]
            self.app.add_url_rule(rule, endpoint, view_func, methods=methods)

    def run(self, port=5000, debug=True):
        self.app.wsgi_app = LoggingMiddleware(self.app.wsgi_app)
        self.app.run(port=port, debug=debug)


if __name__ == "__main__":
    app = WebApp("secret_key")
    app.run()
