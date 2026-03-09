import http.server
import socketserver

PORT = 8080
print("\n  Open in browser:  http://localhost:{}\n".format(PORT))

with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.\n")
