# CFDE-Submit

The `cfde-submit` tool is a product of the NIH [Common Fund Data Ecosystem (CFDE)](https://www.nih-cfde.org/) Coordinating Center (CFDE-CC).

This lightweight command-line tool enables an authorized NIH Common Fund Data Coordinating Center (DCC) to submit a C2M2 instance to CFDE-CC so the DCC's data holdings can be included in the CFDE Portal.

The `cfde-submit` tool works with the CFDE Portal and cannot be used with other systems. Its use is authorized by the CFDE-CC team: only authorized individuals may submit C2M2 instances using `cfde-submit`. See the Getting Started section for information about obtaining authorization.

## Table of Contents

* [Install](#Install)
* [Get started](#Get-started)
 * [About CFDE](#About-CFDE)
 * [Register your DCC](#Register-your-DCC)
 * [Obtain authorization to use cfde-submit](#Obtain-authorization-to-use-cfde-submit)
 * [Prepare your C2M2 instance](#Prepare-your-C2M2-instance)
 * [Find your DCC's identifier](#Find-your-DCC's-identifier)
* [Use the tool](#Use-the-tool)
 * [Login](#Login)
 * [Run](#Run)
 * [Status](#Status)
 * [After your submission](#After-your-submission)
 * [Logout](#Logout)

## Install

See the [Install Guide](./install/index.md) for installation instructions.

## Get started

This section covers everything you need to do after you've installed the `cfde-submit` tool and before you use it to perform a submission. If you are using `cfde-submit` on behalf of a single DCC, all of this will only happen one time. Otherwise, you'll likely need to do most of this whenever you submit on behalf of a new DCC.

### About CFDE

The [Common Fund Data Ecosystem (CFDE)](https://www.nih-cfde.org/) is an initiative of the National Institutes of Health's Common Fund. The Common Fund sponsors several large biomedical initiatives that either span multiple institutes or have no institute as a home. Each of these initiatives is focused on a specific biomedical research issue. For example, the [Kids First](https://kidsfirstdrc.org/) initiative is focused on pediatric cancer, and the [SPARC](https://commonfund.nih.gov/sparc/sparc4-sp4) initiative focuses on interconnections and interactions between the human nervous system and specific organs.

Within each Common Fund initiative, a Data Coordinating Center (DCC) is responsible for gathering the data produced by initiative partners and making that data available to the research community at large, subject to data access agreements. Each Common Fund DCC currently uses its own methods and tools to carry out its mission, so researchers who need to access data must work directly with each relevant DCC, and may need to familiarize themselves with several different data access systems.

CFDE is an initiative to simplify the interface between researchers and the data available from Common Fund DCCs. CFDE is developing [a web portal](https://app.nih-cfde.org/) for searching across all of the Common Fund data, and is working with each DCC to develop services that simplify the data access experience for researchers.

To make CFDE's web portal possible, DCCs tell the CFDE Coordinating Center (CFDE-CC) about the data they manage and make available to researchers. CFDE is defining a model that DCCs can use to describe their data holdings: the [Crosscut Metadata Model (C2M2)](https://docs.nih-cfde.org/en/latest/specifications-and-documentation/draft-C2M2_specification_with_Levels/). Once a description of a DCC's data is constructed using C2M2, the DCC delivers this description to the CFDE-CC. The `cfde-submit` tool is the mechanism for delivering a new or revised instance of a DCC's C2M2 description.

### Register your DCC

To submit a C2M2 instance for your DCC, your DCC must first be registered with the CFDE Portal. Contact the CFDE-CC's DCC Engagement team to register your DCC.

### Obtain authorization to use `cfde-submit`

Once your DCC has been registered with CFDE, your Principal Investigator (or designee) will be given the ability to add team members to permission groups for the DCC. To use the `cfde-submit` tool, you must be added to your DCC's Submitters group.  The CFDE-CC's DCC Engagement team can step you and your Principal Investigator through this process.

### Prepare your C2M2 instance

The `cfde-submit` tool takes a valid C2M2 instance as its input. Any any given time, each DCC has a single C2M2 instance visible in the CFDA portal's public views. Of course, you may revise your DCC's C2M2 instance when your DCC's data changes. You may submit several versions of your DCC's C2M2 instance and review each in a private Data Review area in the portal before approving a single instance for use in the public portal views.

Constructing a C2M2 instance requires comprehensive knowledge of your DCC's data. The [C2M2 documentation](https://docs.nih-cfde.org/en/latest/specifications-and-documentation/draft-C2M2_specification_with_Levels/) describes the data model and how to construct a C2M2 instance for your DCC's data.

When using the `cfde-submit` tool, your C2M2 instance must be contained in a folder on your computer, and it must include the JSON Schema document appropriate for the type of C2M2 instance you are submitting. (Level 0 C2M2 instances contain only a master list of files. Level 1 C2M2 instances include relationships between files, biosamples, subjects, projects, and collections.)

*[TODO: Add detail about any extra files that need to be included in the C2M2 datapackage. E.g., DCC and contact info.]*

### Find your DCC's identifier

When using `cfde-submit` to submit a new C2M2 instance, you must enter your DCC's unique identifier, issued by CFDE-CC. You can find this identifier in the CFDE Portal.

*[Provide detailed directions for locating a DCC's identifier.]*

## Use the tool

### Login

### Run

### Status

### After your submission

### Logout
