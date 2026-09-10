# Repository identity and reading conventions

Updated September 10, 2026. The project is now **Autonomous Racing Systems**, at
[`500ft/autonomous-racing-systems`](https://github.com/500ft/autonomous-racing-systems).
Its previous repository name was `RoboRacer`; this is a rename of the same
repository, not a new project or release.

## What the rename changes

The public name, GitHub description, README navigation and active repository
links use the new identity. Historical commits, paper titles, preregistrations,
data, release artifacts, measurements and approval records retain their original
meaning. Legacy package/module names remain valid; repository branding does not
rename an import or command-line API.

To update an existing clone without moving its files:

```sh
git remote set-url origin https://github.com/500ft/autonomous-racing-systems.git
git remote -v
```

GitHub redirects the old repository location. Do not create a replacement under
the old name: that would remove the redirect. See
[GitHub's rename guidance](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository).
Historical source URLs and immutable evidence records are intentionally not
mass-edited just to remove the former name.

## Reading routes

The [README](../README.md) is the project overview.
[Start here](START_HERE.md) offers short paths for readers, technical reviewers
and contributors. Detailed claims remain in their source documents; an overview
does not replace the authoritative protocol or task ledger.

## Visual provenance

[`media/project-overview.svg`](media/project-overview.svg) is an original,
editable conceptual diagram created for the repository presentation. It contains
no measured values, synthetic plots or purported hardware photographs.
Sources for its relationships: [Integrated report](../reports/final_report.md) and [figure provenance](data-and-figures.md).

Each stage carries an explicit text label. Meaning does not depend on red/green
color differences. The diagram has an SVG title and description; its caption and
the adjacent README text state the evidence limits. Existing analytical figures
retain their original files, generators and provenance contracts.

## Keeping navigation reproducible

From the repository root:

```sh
python tools/check_presentation.py . "Autonomous Racing Systems" autonomous-racing-systems
python tools/test_presentation.py
```

CI runs these checks alongside the existing project gates. They check the README,
reading guide, identity note, contribution guide and figure guide: local paths,
anchors, canonical title/CI badge, image alternative text and SVG accessibility.
Four offline cases confirm valid input passes while missing links, wrong anchors
and identity/accessibility errors fail. This is a bounded presentation checker,
not an exhaustive Markdown parser, external-link crawler or scientific validator.

## Presentation references

The organization is informed by these examples, reviewed September 10, 2026:

- [Best-README-Template](https://github.com/othneildrew/Best-README-Template):
  a readable introduction, navigation and actionable getting-started sections.
- [Cookiecutter Data Science](https://github.com/drivendataorg/cookiecutter-data-science):
  distinct paths for data, analysis and reports.
- [gym-pybullet-drones](https://github.com/learnsyslab/gym-pybullet-drones):
  reproducible use, environment boundaries and source/citation entry points.

The text and overview diagram are project-specific; no template screenshot,
branding, claim of adoption or unrelated technology badge is borrowed.
These presentation changes do not change this repository's existing licensing,
grant permission for hardware tests, or establish a publication/validation verdict.
