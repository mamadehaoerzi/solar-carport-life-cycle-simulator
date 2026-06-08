# Solar Carport Life-Cycle Simulator

A small Python/Streamlit research prototype for a photovoltaic solar carport with battery storage and EV charging infrastructure.

This tool was developed as a digital extension of my master thesis work at the University of Florence.

It allows the user to change technical and economic parameters and see simplified LCA, cost and scenario results.

The public version contains only code and illustrative sample assumptions. It does not include exported data from ecoinvent, Activity Browser, EcoQuery or any licensed LCA database.

## What the tool does

The prototype can be used to explore:

* annual PV generation
* EV charging demand
* demand coverage
* simplified embodied CO2 results
* replacement scenarios
* electricity-only cash-flow results
* circularity-oriented assumptions
* selected LCIA contribution charts

## Case study background

The prototype is inspired by a photovoltaic solar carport case study located at the University of Florence / MOVING Lab area in Calenzano, Italy.

The reference system includes:

* photovoltaic modules
* battery storage
* hybrid inverter
* EV charging devices
* steel carport structure
* concrete ballast
* external power cables
* auxiliary components

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

On Windows, you can also double-click:

```text
start_app.bat
```

## Data import

The app supports two optional CSV uploads:

* `data/sample_component_factors_template.csv` for component-level embodied CO2 factors
* `data/sample_lcia_contributions_template.csv` for LCIA contribution charts and metric cards

The included CSV files are placeholders for formatting only.

Users can replace them with data that they are legally allowed to use.

## Important data note

This repository does not include:

* ecoinvent datasets
* Activity Browser exports
* EcoQuery outputs
* supplier documents
* confidential thesis files
* full thesis documents
* private project spreadsheets

Do not commit files exported from licensed databases unless your license explicitly allows public publication.

Keep private database exports, project-specific models, spreadsheets and generated result files outside the public repository.

## Limitations

This is not a certified LCA model.

It is not validated industrial software.

It is not a commercial investment tool.

It is a small research demonstrator for early-stage scenario exploration.

The results depend on the assumptions and factor tables provided by the user.

## Tools used

* Python
* Streamlit
* pandas
* NumPy
* Altair

## Author

Guansheng Zhang
Master’s student in Mechanical Engineering for Sustainability
University of Florence

## Project status

Prototype version for PhD application and research demonstration.
