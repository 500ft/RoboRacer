# RoboRacer — CAD item list

Prepared 2026-09-06 (America/New_York). **A list of planned parts and assemblies—not completed CAD, hardware or approval to fabricate/test.**

Prioritize the mast, root clamp and static measurement fixture. Confirm their actual interfaces and metrology first; full deck packaging is not a prerequisite.

## How to use this list

This is a parts inventory, not another task-status ledger or additional scope/budget. Each row maps to the [existing work-order definitions](https://github.com/500ft/RoboRacer/blob/cbfbd91c974a718314f3833e02c5b48cdc9a77e3/docs/CAD_PLAN.md) and [their task ledger](https://github.com/500ft/RoboRacer/blob/cbfbd91c974a718314f3833e02c5b48cdc9a77e3/docs/CAD_TASKS.csv); several parts can belong to one work order. Bought parts and existing models should be reused/imported when authorized, not redesigned merely to fill a CAD folder. One part may serve multiple listed interfaces; avoid duplicating it.

## First modeling package: mast and compliance-test fixture

| Item to model or import | Existing work order | Purpose / boundary |
| --- | --- | --- |
| LiDAR mast tube | `RR-CAD-04` | Model the selected stock-tube geometry, datums and measured-as-built revision when available; do not treat nominal CAD as an inspected specimen. |
| Mast root clamp and mounting base | `RR-CAD-04` | Include clamp engagement, fasteners and the mating interface needed for the bench specimen. |
| LiDAR mounting bracket / top interface | `RR-CAD-04` | Define sensor mounting and the actual load/optical-center height. |
| Two-axis static loading fixture | `RR-CAD-05` | Provide load application and clearance in both orthogonal directions. |
| Force-sensor mount and load-line connector | `RR-CAD-05` | Keep calibrated force aligned with the registered load point. |
| Independent tip and root indicator supports | `RR-CAD-05` | Provide matched-resolution reference stations and a way to observe/bound root rotation; a single root translation measurement does not remove rotation. |
| Fixture alignment and inspection datums | `RR-CAD-05`, `RR-CAD-06` | Define force height, clamp orientation, measurement baselines and as-built inspection locations. |
| Complete mast/fixture assembly and FEA handoff geometry | `RR-CAD-06`, `RR-CAD-07` | Supply assembly/section views, drawings and boundary-condition geometry; keep ideal-beam and detailed/as-built models separately identified. |

## Later: vehicle integration

| Item to model or import | Existing work order | Purpose / boundary |
| --- | --- | --- |
| Vehicle electronics deck and component mounts | `RR-CAD-03` | Place compute, batteries, LiDAR assembly and other selected hardware only after the measurement package is reviewed and vehicle integration is promoted. |

## What to deliver for each applicable part or assembly

- Editable/source CAD or an authorized immutable CAD-document version; identify reused vendor geometry and its source.
- STEP export, with dimensions/units checked after reimport. Parameter-driven families also need the planned numerical geometry tests before model acceptance.
- A dimensioned drawing for custom fabricated parts, with material/process, critical fits and inspection datums; vendor hardware can use its sourced drawing.
- An assembly/section view showing how the part fits and which problem it addresses. Label all visuals CAD/design-only until corresponding evidence exists.

The fixture-readiness work order requires stiffness, root-motion observability and a filled uncertainty budget. Actual as-built reference predictions must be committed before campaign loading. CAD/export completion is not physical validation.

## Policy and scope

This checklist-only PR does not copy the pending CAD planning ledgers onto main. The cited work orders live at their existing public commit; linking them does not turn a public branch into private storage. No withheld details are restored, no model task is marked done and no hardware/fabrication/disclosure gate is closed by adding this list.
