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

## 3. Localhost vs. a Domain Name (Does a domain mean it's public?)

A common point of confusion is what a domain name actually means for security.

### What is Localhost?
`localhost` is a special networking term that literally means "this exact computer right here." 
If you run your app on `localhost:5174`, the only person in the entire world who can access it is you, sitting at that specific keyboard. It is perfectly secure, but useless for a team of 5-6 staff members.

### What is a Domain?
A domain name (like `registration.yourorg.org`) is simply a human-readable label that points to an IP Address. It is a phone book entry.

### Does having a Domain mean my app is on the public internet?
**No.** This is a critical point.

You can configure an "Internal DNS" (like a private company phone book). In this setup, if someone at home types `registration.yourorg.org`, it will fail. But if they are in the office building, or connected to the company VPN, the company's private router knows that `registration.yourorg.org` points to `192.168.1.50` (the IP address of your internal server).

A server is **only** exposed to the public internet if:
1. You explicitly open your network firewalls to allow outside traffic in.
2. You put the domain in a public, global DNS registry pointing to a public IP.

By using a domain name instead of localhost, you are simply giving your internal team an easy-to-remember name to access the server over the private network. It does not automatically make the server public.

---
