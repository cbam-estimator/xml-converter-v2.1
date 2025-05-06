# Specs & Co

## Specs

### Version Control

automatischer Umgang mit verschiedenen Versionen des templates

### Installations

must be able to handle installations. If no installations are given, the importer information is used

### procedures

must be able to handle given procedures, in case of 51/54 it must use the additional information about
inward processing. All information must be aggregated in a correct manner

### indirect representative

Different scenarios:

_Normal report_: (Declarant Role 01)

- declarant = importer on header level ; no indirect customs representative

_Indirect representative_: (Declarant Role 02)

declarant has no own imports within the report, otherwise 03 ! <- necessary

- global : declarant = customs repr.
- local : different importers

_No Importer_:
There is no importer given at all

- call austria ; is no imoprter possible

We will receive multiple customer templates that need to be unified in one report
Importer is stated on CN-Code level

### better preprocessing, checks and warnings

### calculation of emission values without the calc excel

### statistics & logs

### note function @ customer

- what changes were made

## Dump

Future goals:

- auto validation within the portal using shadow browser
