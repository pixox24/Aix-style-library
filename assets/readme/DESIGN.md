# README visual sources

- Audience: creators choosing a visual direction and developers integrating the Skill.
- Value: select a stable style ID, then apply its visual components while preserving the requested scene.
- Proof: actual style thumbnails and three real cross-subject generation samples.
- First action: inspect a style with `get --id 0001`, or copy a natural-language invocation.
- Theme: a dark editorial gallery, `#0a0b0d` background, `#f3f5f2` text, `#ccff33` accent.

`hero.svg` is a deterministic title, with no scripts, fonts, or external image dependencies. The five images in `style-spectrum.webp` are the library's original thumbnail files, ordered Aix0001 / Aix0012 / Aix0003 / Aix0111 / Aix0006. IDs, names and categories remain selectable text in the README. The gallery makes no cross-model quality claim.

Rebuild the title and galleries from the repository root:

```bash
python tools/build_readme_assets.py
```

This uses Pillow from `requirements-dev.txt`. `cross-subject.webp` contains Aix0006 samples 01, 03 and 05 from `evaluation/results/0.2.0/images/`, ordered person / object / scene. All gallery sources are included in the main repository; the separate private Web repository is not needed.

Keep essential copy in Markdown. Preview at a 900 px content width and a 360 px mobile viewport, on both light and dark page backgrounds. These assets have opaque backgrounds and work in either GitHub theme.
