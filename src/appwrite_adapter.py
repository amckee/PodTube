import asyncio
import json
from urllib.parse import urlencode

import tornado.httputil
import tornado.web


class AppwriteConnection:
    """
    A mock connection to capture Tornado's response.
    """
    def __init__(self):
        self.status_code = 200
        self.headers = tornado.httputil.HTTPHeaders()
        self.chunks = []
        self.finished = asyncio.Event()

    def write_headers(self, start_line, headers, chunk=None, callback=None):
        self.status_code = start_line.code
        self.headers.update(headers)
        if chunk:
            self.chunks.append(chunk)
        if callback:
            callback()

    def write(self, chunk, callback=None):
        self.chunks.append(chunk)
        if callback:
            callback()

    def finish(self):
        self.finished.set()

    def set_close_callback(self, callback):
        pass

    @property
    def body(self):
        return b"".join(self.chunks)


class AppwriteAdapter:
    """
    Adapter to run Tornado Application on Appwrite Functions.
    """
    def __init__(self, application: tornado.web.Application):
        self.application = application

    async def handle(self, context):
        req = context.req
        res = context.res

        # Prepare URI
        path = req.path
        if req.query:
            if isinstance(req.query, dict):
                query_string = urlencode(req.query)
            else:
                query_string = str(req.query)
            uri = f"{path}?{query_string}" if query_string else path
        else:
            uri = path

        # Prepare Headers
        headers = tornado.httputil.HTTPHeaders(req.headers)

        # Prepare Body
        body = req.body
        if isinstance(body, dict):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        elif body is None:
            body = b""

        connection = AppwriteConnection()
        
        # Create Tornado Request
        tornado_request = tornado.httputil.HTTPServerRequest(
            method=req.method,
            uri=uri,
            version="HTTP/1.1",
            headers=headers,
            body=body,
            host=req.host or "localhost",
            connection=connection # type: ignore
        )

        # Execute Request
        # Tornado Application.__call__ starts the request processing
        self.application(tornado_request)
        
        # Wait for finish
        await connection.finished.wait()

        # Convert back to Appwrite response
        response_headers = dict(connection.headers)
        
        # We use binary() to ensure all types of data are handled correctly
        return res.binary(
            connection.body,
            connection.status_code,
            response_headers
        )
