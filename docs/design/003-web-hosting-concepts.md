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

## 2. What is a "Reverse Proxy" (like Caddy or Nginx)?

We want to get rid of CORS entirely because it causes headaches and security risks. To do that, we need to trick the browser into thinking the React app and the Backend are on the **exact same Origin**.

But a computer cannot run two different programs on the exact same port. You can't put React on `localhost:80` AND the backend on `localhost:80` at the same time. 

### The Solution: A Traffic Cop
A Reverse Proxy (like Caddy or Nginx) is a piece of software that sits at the very front of your server, listening on a single port (like port 443 for HTTPS). It acts as a traffic cop.

When a user types `https://registration.yourorg.org` into their browser, the request hits the Reverse Proxy first. 

The proxy looks at the URL path and directs traffic internally:
- If the user asks for `/` (just the website), the proxy says: *"Ah, you want the website. Let me grab the React files for you."*
- If the React app sends data to `/grpc/save_user`, the proxy says: *"Ah, this starts with /grpc/. Let me forward this invisibly to the backend program."*

### Why this is brilliant:
To the web browser, everything is happening on `https://registration.yourorg.org`. It doesn't know that behind the scenes, there are two different programs. 
Because the browser sees only **one origin**, the Same-Origin Policy is satisfied. **CORS errors disappear completely.** You don't need `allow_origins=["*"]` anymore. It is instantly highly secure.

---

## 3. Same Domain React App Hosting

### How are you running React right now?
Currently, you run `bun run dev`. This starts a "Development Server" built by a tool called Vite. This server is heavy. It watches your files, and if you type a new line of code, it instantly refreshes your browser. It is amazing for writing code, but it is **terrible** for production. It is slow, uses too much memory, and isn't designed to handle real users.

### How it should be in Production
When you are ready for production, you run a command called `bun run build`. 
This command takes all your fancy React code, squishes it down, removes all the development tools, and spits out pure, simple, static files: `index.html`, some `.js` files, and some `.css` files.

These are just dumb, static files. They don't need a heavy Node.js or Bun server to run them. 

### "Same Domain Hosting"
Instead of paying for a separate service to host these static files, we just take those files and hand them to our Reverse Proxy (Caddy/Nginx). 

We tell the Reverse Proxy: *"If someone visits the website, just hand them these static files."*

This is what "Same Domain Hosting" means. Your frontend (the static files) and your backend (the Python code) are living on the exact same server machine, being served by the exact same traffic cop (Caddy/Nginx) under the exact same domain name.

---

## 4. Do we need a CDN?

**Short answer: No.**

### What is a CDN?
CDN stands for Content Delivery Network. 
Imagine you build Netflix. You have users in Tokyo, London, and New York. If your server is in New York, the users in Tokyo will experience a long delay waiting for the website files to travel across the ocean. 

A CDN takes your static files (like your React `index.html` and images) and copies them to hundreds of servers all over the globe. That way, the user in Tokyo downloads the website from a server physically located in Tokyo. It makes public websites lightning fast.

### Why you don't need it
Your project scope:
- It is an **in-house** application.
- It is used by a small team of **5-6 staff members**.
- They are likely sitting in the same office, or at least in the same country.

Adding a CDN adds extreme complexity to your deployment process. You have to write scripts to clear the CDN memory every time you update the app, and you have to pay for a third-party service. 

For 5-6 internal users, the Reverse Proxy (Caddy/Nginx) serving the files directly from your single server is incredibly fast, practically free, and infinitely easier to manage.
