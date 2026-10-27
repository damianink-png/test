# Offline section view
Original WebGL clipping implementation inspired by three.js clipping-plane functionality:
https://threejs.org/docs/pages/Material.html#clippingPlanes
https://threejs.org/examples/webgl_clipping.html
No third-party source copied or library added to the application.

X/Y/Z, 0–100% slider, flip side, disabled by default. One model-space plane is applied identically to rendering, transparent old parts, highlights and picking. No new B-Rep operations or STEP changes. This is a visual cutaway without capped cut faces, not a measurable CAD section.

Local: 18 axis/position/flip combinations plus JS syntax passed. Chromium installation failed in the local environment; actual Edge WebGL screenshots and restoration are tested by Windows CI before packaging the application. The workflow preserves the integrated proof/matching source and all its regression gates; it does not duplicate ongoing six large CAD tests for a viewer-only change.
