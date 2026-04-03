# 雷霆AI tutor

A 3D explorable scene built with three.js and Blender. Based on the [intro course](https://www.youtube.com/watch?v=X3pPAdQBKHo) to creative web development with three.js and Blender.

**The 3D background** (the scene in `background.glb`) is created and edited in **Blender** (and any other 3D tools you use). The rest of the project—HTML, JavaScript, CSS, and the server—loads and runs that scene in the browser; it does not edit the 3D background itself.

## What each file does

| File | Purpose |
|------|--------|
| **index.html** | Main page: layout, loading screen, theme/audio toggles, and script loading (including the three.js import map). |
| **main.js** | Game logic: loads the 3D scene (`background.glb`), character movement, collision, camera, clickable objects, modals, and audio. |
| **style.css** | All visual styling: layout, loading screen, theme (light/dark), buttons, and modal appearance. |
| **start_server.py** | Simple Python HTTP server so the app and assets (GLB, sounds) load correctly in the browser. |
| **background.glb** | 3D scene (place in project root). Must contain a `Character` object for spawn; the rest is used for collision. |
| **sfx/** | Sound files (e.g. `music.ogg`, `projects.ogg`, `jumpsfx.ogg`) used for background music and effects. |
| **LICENSE.md** | License text for the project. |
| **background.blender** |(the scene in `background.glb`) is created and edited in Blender, you can find in Other to edit it.

## How to open the server

1. Open a terminal in the project folder.
2. Run:
   ```bash
   python start_server.py
   ```
   (On some systems you may need `python3` instead of `python`.)
3. In your browser, go to: **http://localhost:8080**(Often you need to wait like 2 min to open it, don't freak out if you are still loading)

Stop the server with `Ctrl+C` in the terminal.

## Inspo

- [Character](https://www.freepik.com/premium-photo/pixel-girl-surfing-voxel-art-surfboard-dolly-kei-style_165308006.htm)
- [Crossy Road](https://crossyroad.fandom.com/wiki/Crossy_Road_Wiki)
- [Bruno Simon](https://bruno-simon.com/)
