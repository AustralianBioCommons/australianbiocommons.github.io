ToolFinder
==========

## Description

The purpose of ToolFinder is to present a landscape view of bioinformatics software packages & tools 
installed across Australian national computational infrastructures, including:

- [National Computational Infrastructure](https://nci.org.au/) (NCI)
- [Pawsey Supercomputing Centre](https://pawsey.org.au/) (Pawsey)
- [Queensland Cyber Infrastructure Foundation](https://www.qcif.edu.au/) (QCIF) / [QRISCloud](https://www.qriscloud.org.au/)
- [Galaxy Australia](https://usegalaxy.org.au/)

ToolFinder also:

1. Presents relevant metadata for each of these tools, which is sourced from [bio.tools](https://bio.tools/),
2. Provides connections to other global registries as appropriate, and based on user feedback (e.g. [BioContainers](https://biocontainers.pro/)), and
3. Provides, where possible, the ability to directly access (or `launch`) bioinformatics tools. The **only** current example of this is for [Galaxy Australia](https://usegalaxy.org.au/).


## Diagram


## How to cite this software

> Add citation instructions here.


## User guide


### General build description

ToolFinder takes a curated list of bioinformatic software packages/tools, imports this list and 
uses a unique identifier to add metadata from bio.tools, and infrastructure specific tool information, 
for the above listed Australian national computational infrastructures.

For example, for Galaxy Australia this entails the `tools available`, and for the high performance 
computing infrastructures this entails the `version(s) available` for each software package.

It is recommended to use an IDE like [**pycharm**](https://www.jetbrains.com/pycharm/) to maintain and further develop ToolFinder.


### Required (minimum) inputs / parameters

The essential steps required to rebuild ToolFinder are:

1. A complete copy of this repository: https://github.com/AustralianBioCommons/australianbiocommons.github.io
2. A series of minimum input files in the folder called `external` - these are listed in the `Required (minimum) inputs/parameters` section below

> **Note:** some data is imported by interacting with an external API. 
> This includes metadata from **bio.tools**, **Galaxy Australia**, and **NCI**.

| Source                | Type                                                        | Input(s) to ToolFinder                                                                      | Location? | Curation required?|
|-----------------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------------|:---:|:---:|
| Australian BioCommons | BioCommons Tool Matrix                                      | `Matrix_of_Availability_of_Bioinformatics_Tools_across_BioCommons__deployment_version.xlsx` | `external` folder |**Yes**|
| bio.tools             | Registry metadata                                           | https://bio.tools/api/t/                                                                    | None - API | **Yes** |
| Galaxy Australia      | Infrastructure API                                          | https://usegalaxy.org.au/api/tools                                                          | None - API | No |
| Australian BioCommons | Galaxy Tools Matrix - used to match Galaxy tool IDs to Tool Matrix IDs | `galaxy_tools_curation.csv`                                                      | `external` folder | **Yes** | 
| NCI                   | Infrastructure apps-service                                 | http://gadi-test-apps.nci.org.au:5000/dump                                                  | None - API | No |
| NCI                   | Infrastructure apps-service for shared repository `if89`    | http://130.56.246.237:5000/dump                                                             | None - API | No |
| NCI                   | API key file                                                | `gadi.key.hdr`                                                                              | `external` folder | No |
| NCI                   | API key file for `if89`                                     | `bioapps_token.txt`                                                                         | `external` folder | No |
| Pawsey                | Infrastructure module list                                 | `setonix.txt`                                                                               | `external` folder | No |
| QCIF / QRISCloud      | Infrastructure module list                                  | `qriscloud.txt`                                                                             | `external` folder | No |


### Dependencies & third party tools 

Install of the following is required to maintain and develop ToolFinder locally:

- Python (3.8)
- R (4.1.2)
- pycharm (2021.2.3)

ToolFinder also depends on multiple APIs, including:

- bio.tools: https://bio.tools/api/tools/ 
- Galaxy Australia: https://usegalaxy.org.au/api/tools
- NCI: http://gadi-test-apps.nci.org.au:5000/dump

If any of these are changed, then this will also impact the operation of ToolFinder.


## Additional notes

Any comment on major features being introduced, or default/API changes that might result in unexpected behaviours.


## Help / FAQ / Troubleshooting


## Tutorials

Please see these video tutorials available through the Australian BioCommons YouTube Channel:

- [Australian BioCommons ToolFinder](https://www.youtube.com/watch?v=yzsH6PEXqC4)
- [Australian BioCommons technical documentation quick tour](https://www.youtube.com/watch?v=UPIaNleejRk&t)


## [License](LICENSE)


## Acknowledgements / citations / credits

This work is supported by the [Australian BioCommons](https://www.biocommons.org.au/) via funding from [Bioplatforms Australia](https://bioplatforms.com/), the Australian Research Data Commons (https://doi.org/10.47486/PL105) and the Queensland Government RICF programme. Bioplatforms Australia and the Australian Research Data Commons are funded by the National Collaborative Research Infrastructure Strategy (NCRIS).

Tool metadata is sourced from [bio.tools](https://bio.tools/) where possible

> Ison, J. et al. (2015). Tools and data services registry: a community effort to document bioinformatics resources. Nucleic Acids Research. [DOI](https://doi.org/10.1093/nar/gkv1116)

> [bio.tools API](https://biotools.readthedocs.io/en/latest/api_reference.html)

EDAM is used for tool list categorisation

> Ison, J., Kalaš, M., Jonassen, I., Bolser, D., Uludag, M., McWilliam, H., Malone, J., Lopez, R., Pettifer, S. and Rice, P. 2013. EDAM: an ontology of bioinformatics operations, types of data and identifiers, topics and formats. Bioinformatics, 29(10): 1325-1332. [DOI](https://doi.org/10.1093/bioinformatics/btt113) PMID: 23479348 *Open Access*

> [EDAM ontology GitHub](https://github.com/edamontology/edamontology)

