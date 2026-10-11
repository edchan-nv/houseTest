# HouseTest — 1172 Millbrae Avenue

An editable OpenUSD architectural study and a static, mobile-friendly tour. All views are rendered with NVIDIA OVRTX. Visitors need neither a GPU server nor a VPN.

The model follows the listing floor plan and photographs. It is a stylized reconstruction, not a measured survey or a photoreal replica. Heights, roof junctions, terrain, material response, and furniture shapes are inferred. See `scene/provenance.json`.

## What works

- 11 room viewpoints and three rotating exterior/floor views.
- Furnished/empty presets plus independent seating, tables, beds, and decor visibility in room views.
- 24 pre-rendered rotation positions for exterior and floor views; fixed viewpoints for interiors.
- 74 individually editable staging item parents in USD and Blender.
- Permanent architecture, stairs, fixtures, cabinets, and landscaping remain independent of furniture.
- Mobile layout, image-loading/error handling, keyboard rotation, and URL-based view sharing.

The page uses static images, not browser-side 3D rendering. Free navigation or furniture movement requires opening the editable source model or adding a live OVRTX/OVStream service.

## Using the tour on your phone or computer

1. Open the published page. No sign-in or NVIDIA VPN is required.
2. Select **Room tour** and tap a thumbnail to visit one of the 11 room viewpoints.
3. Select **Empty** to remove all staging or **Furnished** to restore it. Room views also offer individual category switches for seating, tables, beds, and decor; disabled switches mean that category is absent from the selected room.
4. Choose **Main level**, **Lower level**, or **Exterior**, then swipe/drag horizontally or use the arrow buttons to rotate in 15° increments. Desktop left/right keyboard arrows work too. Interior room viewpoints remain fixed.
5. Use the expand button where your browser supports fullscreen. Copy the browser URL to share your selected view and staging state.
6. Select **Download the editable model**, unzip it, and open `house.usda` in a USD application or `house.blend` in Blender. Keep `house.usdc` beside the USD entrypoint. Individual item paths are listed in `furniture-prims.json`.

The webpage switches between pre-rendered images. It does not support dragging furniture to new positions or free walking; use the editable source for those changes.

## Local preview

```sh
python3 -m http.server 8765 --directory public
```

Open `http://localhost:8765`. The published site serves the same `public` directory.

## Rebuild the model and renders

Use isolated Blender/OpenUSD and OVRTX Python environments, as described in the project environment inventory. Do not import unrelated USD distributions in the renderer process.

```sh
blender --background --threads 8 --python scripts/build_house.py
sim-python geometry scripts/prepare_renders.py --size 1440
sim-python viewer scripts/render_tour.py
sim-python geometry scripts/package_model.py
python3 scripts/validate_site.py
```

The tested environment uses Blender 5.2.1, OVRTX 0.5.0.377615, OVStage 0.2.0.377349, and an NVIDIA RTX PRO 6000 Blackwell GPU. OVRTX owns rendering and OVStage owns published scene state. Each render uses 96 path-tracing samples; camera and visibility changes are authored in a separate composition. The base asset is hash-checked for mutation. Initial runtime schemas are registered by constructing the renderer before OVStage population in this pinned build.

```sh
npm ci
npm test
```

Start the local preview server before UI testing. `CHROME_PATH` can override the installed Chrome path. `TEST_URL` can target the deployed site. Desktop/mobile screenshots and validation reports live in `evidence/`.

## Model editing

Open `scene/house.usda`. Its `furnishing` variant switches all staging between furnished and empty. Individual item paths are in `scene/furniture-prims.json`; hide or transform each item parent. The native source is `scene/house.blend`. A portable ZIP is available through the tour.

## Source evidence

- [Listing](https://www.redfin.com/CA/Millbrae/1172-Millbrae-Ave-94030/home/665972)
- [Listing floor plan](https://ssl.cdn-redfin.com/photo/8/bigphoto/426/ML82063426_120_1.jpg)

Reference photographs are used locally and are not redistributed in the repository or webpage. Dimensions are estimates, with approximately 0.037 metres per floor-plan pixel. This work has no affiliation with Redfin or the listing agent.

## Hosting

After committing a reviewed change, run `scripts/publish_github.sh` to update the source and Pages branches.

The static page is suitable for GitHub Pages, GitLab Pages, or any HTTPS static host. `scripts/validate_site.py` verifies every referenced render before publication. The included GitLab pipeline is an optional alternative; the current delivery target is GitHub Pages.
