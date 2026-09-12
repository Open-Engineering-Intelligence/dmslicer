# Task naming correction

User-requested correction: architectural responsibility must determine task
classification. The historical 08 series remains geometry-case research and
evidence work. The approved 09 series owns application-workbench UI design.

Research phases remain those in the frozen research contract: interface
detection, volumetric field, and slice-plane sampling. This record does not
modify that contract or claim any phase gate passed.

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
