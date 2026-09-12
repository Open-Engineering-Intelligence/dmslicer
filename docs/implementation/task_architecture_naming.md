# Task naming correction

User-requested correction: architectural responsibility must determine task
classification. The historical 08 series remains geometry-case research and
evidence work. The approved 09 series owns application-workbench UI design.

Research phases remain those in the frozen research contract: interface
detection, volumetric field, and slice-plane sampling. This record does not
modify that contract or claim any phase gate passed.

Project-foundation architecture uses the hierarchical `00-*` series. The
current canonical map is:

| Code | Responsibility |
| --- | --- |
| 00-01 | G1 geometry contract foundation |
| 00-02 | SlicerDecision MVP |
| 00-03 | GeometrySnapshot Viewer MVP |
| 00-04 | 07A to GeometrySnapshot adapter bridge |
| 00-05 | MVP experiment matrix and parallel interface planning |
| 00-06 | workflow map and backend migration manual |
| 00-07 | architecture governance freeze and parallel-development enablement |
| 00-08A..D | ordered P2-MVP evidence-infrastructure subtasks |

Superseded planning-only entries use a traceable suffix such as `00-03P` and
may be archived after their canonical task is identified.

Persistent coordination and voice entry points use a separate `CHAT-*` series.
`DM-Slicer｜CHAT-01 项目协调对话窗口` replaces the former
`DM-Slicer｜08E 几何案例显示工作台` title after its implementation duties
moved to `09A`. The conversation remains available for traceability, while
geometry-viewer implementation and evidence belong to the searchable `09A`
task.

| Previous title | Current title | Goal ID |
| --- | --- | --- |
| DM-Slicer｜08J 材料与语义配置工作区 | DM-Slicer｜09B 材料与语义配置工作区 | WORKBENCH-MATERIAL-SEMANTIC-UI-01 |
| DM-Slicer｜08E 几何案例显示工作台（保留为基线） | DM-Slicer｜09A 几何显示交互重设计（独立任务） | WORKBENCH-GEOMETRY-VIEW-UI-01 |

`09A` owns geometry presentation and interaction: object, interface, and patch
browsing; selection; visibility; opacity; and the evidence drawer. `09B` owns
the material library, material properties, explicit semantic-role assignment,
display colors, and their persistence. `09A` may consume assignments from
`09B`, but neither task may modify geometry truth. Configuration is preparation
for downstream field computation, not evidence that a field solver exists or
Phase II passed.

Existing geometry coverage tasks retain their historical identifiers for
traceability. They remain geometry validation work rather than new research
phases. Future cross-domain tasks must record an owning domain, affected
contracts, dependencies, acceptance criteria, and an unchanged stable Goal ID.
