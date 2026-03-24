# Web Hosting Concepts Explained for Beginners

This guide breaks down exactly what happens when a browser talks to a server, why we need certain technologies (like Caddy/Nginx), and why we are making specific choices for your registration app.

---

## 1. What is an "Origin" and what is "CORS"?

### The Security Problem
Imagine you log into your bank website at `bank.com`. Your browser saves a "session" (like a digital ID card) so you don't have to log in every time you click a new page. 

Now imagine you open a new tab and visit a malicious website called `evil-hacker.com`. If `evil-hacker.com` writes a script that says *"Hey browser, send a money transfer request to bank.com"*, your browser would normally just do it, using your saved ID card. 

To stop this, web browsers invented the **Same-Origin Policy (SOP)**.

### What is an "Origin"?
An Origin is a combination of three things:
1. **The Protocol** (HTTP or HTTPS)
2. **The Domain** (like google.com or localhost)
3. **The Port** (like :80 or :5174)

If **any** of these three things are different, the browser considers them **different origins**.

### What happens in your app right now?
Right now on your computer:
- The React App is running on: `http://localhost:5174` (Origin A)
- The Backend Proxy is running on: `http://localhost:8080` (Origin B)

Because the ports are different, Origin A and Origin B are completely different in the eyes of the browser. 

When your React app (Origin A) tries to send a save request to the backend (Origin B), the browser panics. It says: *"Wait! A script from 5174 is trying to talk to 8080! This could be a hacker!"* and it **blocks the request**.

### What is CORS?
CORS stands for **Cross-Origin Resource Sharing**. It is the official way to tell the browser: *"No, it's okay, Origin A is allowed to talk to Origin B."*

To make this work, before the browser sends your actual data, it sends a hidden "pre-flight" check (called an `OPTIONS` request) to the backend. It asks: *"Hey backend, are you willing to accept data from Origin A?"*

In your current code, you have a line that says `allow_origins=["*"]`. This tells the backend to answer: *"Yes, I accept data from ANY origin in the world (*)."* This is very insecure for a production environment. 

---

## 2. What is an "Edge Web Server" (like Caddy or Nginx)?

We want to get rid of CORS entirely because it causes headaches and security risks. To do that, we need to trick the browser into thinking the React app and the Backend are on the **exact same Origin**.

But a computer cannot run two different programs on the exact same port. You can't put React on `localhost:80` AND the backend on `localhost:80` at the same time. 

### The Solution: A Traffic Cop
An Edge Web Server (often called a Reverse Proxy) like Caddy or Nginx is a piece of software that sits at the very front of your server, listening on a single port (like port 443 for HTTPS). It acts as a traffic cop.

When a user types `https://registration.yourorg.org` into their browser, the request hits the Edge Web Server first. 

The server looks at the URL path and directs traffic internally:
- If the user asks for `/` (just the website), the server says: *"Ah, you want the website. Let me grab the React files for you."*
- If the React app sends data to `/grpc/save_user`, the server says: *"Ah, this starts with /grpc/. Let me forward this invisibly to the backend program."*

### Why this is brilliant:
To the web browser, everything is happening on `https://registration.yourorg.org`. It doesn't know that behind the scenes, there are different programs doing the work. 
Because the browser sees only **one origin**, the Same-Origin Policy is satisfied. **CORS errors disappear completely.** You don't need `allow_origins=["*"]` anymore. It is instantly highly secure.

### Serving the App (Same-Domain Hosting)
Currently, you run `bun run dev`. This starts a heavy development server. When you are ready for production, you run a command called `bun run build`. 
This command takes all your fancy React code, squishes it down, and spits out pure, simple, static files: `index.html`, `.js`, and `.css`.

Instead of paying for a separate service to host these static files, we just hand them to our Edge Web Server (Caddy/Nginx). 

This is what we mean by "Same Domain Hosting". Your frontend (the static files) and your backend (the Python code) are living on the exact same server machine, being handled by the exact same traffic cop under the exact same domain name.

---

## 3. Internal DNS & VPNs (How to have a Domain without the Public Internet)

When moving away from `localhost`, many developers assume they must buy a public domain and expose their server to the internet. This is not true for internal applications.

### VPN (Virtual Private Network)
A Site-to-Site VPN connects multiple physical offices securely over the internet. To the computers inside those offices, it feels like they are plugged into the exact same local Wi-Fi router. The server is completely hidden from the outside world.

### Internal DNS
If you are on a VPN, how do staff type `https://registration.jkp.internal` instead of an ugly IP address like `192.168.1.50`?
- You configure an **Internal DNS Server** (a private phone book).
- Your office router tells every computer: *"Check this internal phone book first."*
- The internal phone book maps `registration.jkp.internal` to `192.168.1.50`.
- The browser hits the Edge Web Server securely without ever touching the public internet.

A server is **only** exposed to the public internet if:
1. You explicitly open your network firewalls to allow outside traffic in.
2. You put the domain in a public, global DNS registry pointing to a public IP.

---

## 5. Python Concurrency & The GIL (Why Web Servers Block)

A common misconception is how Python handles multiple tasks at once. To understand why background queues are necessary, you must understand the GIL.

### The Global Interpreter Lock (GIL)
Unlike C++, where multiple threads can run in parallel on different CPU cores sharing the same memory, Python (specifically standard CPython) has a Global Interpreter Lock. 
- The GIL dictates that **only one thread can execute Python code at a time** within a single process.
- **I/O Bound:** If a thread is waiting on the network or database, it drops the GIL. Another thread can run. This is why Python is great for standard web APIs.
- **CPU Bound:** If a thread is doing heavy math or formatting a 50,000-line CSV, it *holds* the GIL. Every other thread in that process is completely frozen.

### Multi-processing Limits
To bypass the GIL, web servers use **Multi-processing** (running 4 entirely separate Python processes, mapped to 4 CPU cores). 
However, if 4 staff members request massive CSV exports simultaneously, all 4 processes are pinned at 100% CPU. When the 5th staff member tries to load the dashboard, there are no processes left. The server appears dead, and the browser eventually times out.

---

## 6. Decoupling with Background Queues

To solve the multi-processing bottleneck, we use a concept called **Decoupling**. 

### The Bad Way (Synchronous)
1. Browser asks for an Export.
2. The Web Process does the export (takes 3 minutes).
3. Browser waits 3 minutes. (Likely fails due to network timeout limits).

### The Decoupled Way (Asynchronous Queue)
1. Browser asks for an Export.
2. The Web Process instantly writes a tiny note to a database/Redis: `{"task": "export"}`.
3. The Web Process replies to the browser in 5 milliseconds: "Job Started!" (The Web Process is now free for the next user).
4. A completely separate **Worker Process** (which does not answer web requests and has its own GIL) constantly checks the database, sees the note, and spends 3 minutes doing the export in the background.

*Note: We cannot use the local file system (e.g., writing `task.json`) for queues because multiple worker processes will hit race conditions trying to read/delete the same file, and ephemeral Docker containers will delete pending tasks if restarted.*

---

## 7. The Tiers of Caching

When a system is slow, the immediate reaction is often "add Redis". However, caching exists in tiers. The closer to the user you cache, the faster and cheaper it is.

1. **Browser Caching (The Client):** The absolute fastest cache. Tools like React Query save database responses in the browser's RAM. If a user clicks "India" twice, the second click instantly loads the states from local RAM without touching the network.
2. **Edge Web Server Caching (Nginx/Caddy):** The reverse proxy remembers HTTP `GET` responses. However, because gRPC uses `POST` requests with binary data, edge caching is usually technically impossible for gRPC APIs.
3. **In-Memory Server Caching (Python):** Using decorators like `@lru_cache`, the Python process saves data in its own RAM. It bypasses the database completely. The downside is that if you have 4 worker processes, they don't share this memory (Process A doesn't know what Process B cached).
4. **Distributed Caching (Redis):** A dedicated, centralized, lightning-fast RAM database. All 4 Python processes connect to it. It is required when data *must* be instantly consistent across all processes (like Rate Limiting or Session Management), but it adds significant infrastructure complexity.
