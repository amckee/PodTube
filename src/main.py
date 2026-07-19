import sys
from pathlib import Path

import tornado.web

base_dir = Path(__file__).resolve().parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from appwrite_adapter import AppwriteAdapter

class PingHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "text/plain")
        self.write("Pong")

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write({
            "motto": "Build like a team of hundreds_",
            "learn": "https://appwrite.io/docs",
            "connect": "https://appwrite.io/discord",
            "getInspired": "https://builtwith.appwrite.io",
        })
    
    post = get
    put = get
    patch = get
    delete = get

class HealthHandler(tornado.web.RequestHandler):
    def get(self):
        self.write({
            "status": "ok",
            "runtime": "python-3.14",
            "framework": "Tornado 6.5.7",
            "adapter": "AppwriteAdapter v1.1"
        })

def make_app():
    return tornado.web.Application([
        (r"/ping", PingHandler),
        (r"/health", HealthHandler),
        (r"/", MainHandler),
    ])

# Global application and adapter instance
app = make_app()
adapter = AppwriteAdapter(app)

async def main(context):
    # You can still use the Appwrite SDK here if needed
    # client = Client()...
    
    # Delegate to Tornado via the adapter
    return await adapter.handle(context)
