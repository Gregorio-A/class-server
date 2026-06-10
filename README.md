# Class-Server V2

A local server to share web projects in the classroom with quick QR Code access.

The main focus of the app is to allow teachers to open an HTML/CSS/JS project on their own computer and share this server with students on the same network, without needing to repeat IP, port, user[...]

---

## Overview

**class-server v2** is a local development server built with Python using FastAPI, Uvicorn, WebSocket, Watchdog, and QR Code.

It serves files from the current folder, automatically injects a reload script into HTML pages, and allows multiple devices on the same network to view the project during class.

<img width="1601" height="864" alt="image" src="https://github.com/user-attachments/assets/49ddf93e-de32-4aa0-9a23-95978c0aa99e" />

---

## Main reason for creation

In the classroom, sharing a local project is usually tedious:

* the teacher needs to discover the machine's IP;
* needs to choose a free port;
* needs to explain the address to all students;
* needs to deal with typos;
* needs to manually refresh the page with each change;
* needs to minimally control who can access;
* needs to avoid exposing the server insecurely.

This app solves this workflow with a simple idea:

> Run the server on the teacher's computer and generate a temporary QR Code for students to quickly access the project.

In practice, the QR Code works as a "gateway" to the classroom server.

---

## What the server does

* Serves static files from the folder where the command was executed.
* Opens `index.html` automatically when a folder is accessed.
* Blocks directory listing.
* Prevents access to files outside the project root folder.
* Generates username and password for HTTP Basic authentication.
* Generates a random password automatically when no password is provided.
* Generates temporary token for QR Code login.
* Creates authentication cookie for those accessing via QR Code.
* Creates a secure token-protected WebSocket for live reload.
* Reloads the page when HTML/JS or other files are changed.
* Updates CSS without reloading the entire page.
* Updates images without reloading the entire page.
* Preserves scroll position after reload.
* Preserves values of inputs, textareas, and selects after reload.
* Ignores heavy folders like `node_modules`, `.git`, `.venv`, `dist`, and `build`.
* Uses debounce to avoid multiple consecutive reloads.
* Generates self-signed SSL certificate when running on HTTPS.
* Falls back to HTTP if certificate creation fails.
* In HTTP mode, limits access to `localhost` for security.
* Automatically finds a free port when the default port is already in use.
* Creates Python virtual environment automatically.
* Installs dependencies automatically via `pip`.
* Generates optional VS Code integration using `tasks.json`.
* Saves logs to `live_server.log`.

---

## Quick start

```bash
python server.py --open
```

With custom port:

```bash
python server.py --port 3000 --open
```

With custom username and password:

```bash
python server.py --user professor --password aula123 --open
```

---

## Common problems and solutions

| Problem                 | Likely cause                                    | Solution                                                       |
| ----------------------- | ----------------------------------------------- | -------------------------------------------------------------- |
| Mobile device can't access | Different networks, firewall, or router isolation | Put everyone on the same network and open the port              |
| Certificate warning     | Self-signed HTTPS                               | Accept warning in local environment or generate proper certificate |
| QR Code doesn't appear  | Terminal doesn't render well                    | Use another terminal or copy the URL manually                   |
| WebSocket doesn't reload | Certificate/firewall/cache                      | Scan the QR code again and check firewall                       |
| Dependencies fail       | `pip`, internet, or proxy                       | Install manually with `pip install`                            |
| VS Code task fails      | Script outside project root                     | Place script in correct folder or adjust `tasks.json`           |

---

## Security notes

* The QR Code grants access to the project while the server is running.
* The server shares the current folder, so don't run it inside directories with personal files.
* Avoid keeping `.env`, `.key`, `.pem`, local databases, or backups inside the served folder.
* HTTP mode only runs locally to prevent sending credentials without encryption over the network.
* The app is designed for classroom use and local development, not for production.

---

## Technical conclusion

The server functions as a bridge between the teacher's computer and the students' devices.

It solves the practical problem of sharing a local project in the classroom with less friction: QR Code, temporary authentication, live reload, and access via the local network.

It doesn't replace real hosting or production deployment. The proposal is to be a fast, portable, and efficient tool for demonstrations, HTML/CSS/JS lessons, mobile testing, and remote follow-up [...]
