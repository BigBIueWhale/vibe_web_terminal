# Project Instructions (Verbatim)

You know what? Fine. Let's say I do want to use Vibe CLI. The issue is that I want to serve it on a local network and because I want to avoid installations (due to version drift), I want the CLI interface to be available online, on a website! With ability to upload files for Mistral Vibe CLI to use. Of course, I want to run this in interactive mode. Somehow like a whole keyboard-respecting terminal within the browser, and all displaying and controlling live a temporarily spawned docker image that runs Vibe CLI but like, in a way that kind of knows how to route it to the web pagee, and control it from the web page. This is a very challenging task. The idea is to make it kind of spawn a docker image. I just installed docker for you. It should obviously all be automated, running this Vibe CLI instance in a rich Ubuntu docker image environment with a bunch of things preinstalled, and the docker instance created should be highly temporary, and automatically run this dedicated application that you'll create that kind of controls Vibe CLI. Kind of like a server that controls and streams the terminal from one vibe CLI instance. Then there's the main server that handles all Vibe CLIs that are running in the docker images, and kind of routes to the web pages of people who have sessions opened. The implementation should truly be full, and the most tricky thing is getting the terminal thing right. Maybe even route SSH or something? SSH seems to get terminal keyboard stuff right, maybe learn from that and somehow put that as web frontend. Like, ideally we just give users terminal that already happens to have vibe open. Yes! This is so much simpler. it's a website that anyone connecting gets a newly spawned docker image (and they get a hash ID in the URL so they can return to that docker image instance), and they can even exit vibe CLI then type anything they want into the terminal!! Password should be "password" within this machine! Yes, this is so generic and good. Then the whole AI thing with Vibe CLI sure- it has to be set up to actually work with our local Ollama Load Balancer server, but it's quite generic- it's literally just giving high quality linux terminal to whoever connects to a website!! I'm pretty sure you understand the purpose here.

## Summary of Requirements

1. **Web-based terminal** - Full keyboard support, colors, TUI apps
2. **Docker containers** - Ephemeral, spawned per user session
3. **Session persistence** - Hash ID in URL allows returning to same container
4. **Vibe CLI pre-configured** - Connected to local Ollama Load Balancer (172.17.0.1:11434)
5. **Generic Linux terminal** - Users can exit vibe and use full shell
6. **Password: "password"** - For the container user
7. **File upload capability** - For Vibe CLI to work with user files
8. **Local network accessible** - Serve on LAN

## Additional Requirements (Added Later)

9. **Robust large file/folder upload** - From website to container's home directory or accessible folder
10. **HTTP-based** - All running on HTTP when accessing website
11. **Responsive and realtime** - Actual terminal experience, not just cursor streaming
12. **Scrollback buffer** - Up to 10,000 lines
13. **Smart scroll behavior** - Don't snap to bottom when content is printed, but DO follow if already at bottom
14. **Extremely robust** - Should work like a real terminal
