# CV Tailor

FastAPI application used to:
- store a master CV profile and cover letter
- create or import opportunities
- generate a tailored resume and adapted cover letter
- search for PhD opportunities from multiple sources
- manage source onboarding through an integration chat assistant

The application is served with Docker Compose and exposes a simple UI at `/ui`.

## Features

### CV / profile
- user registration and login
- master CV storage in plain text or LaTeX
- optional master cover letter storage in plain text or LaTeX
- PDF compilation of the master CV when LaTeX is available
- optional GitHub username validation

### Tailoring
- manual job posting creation
- CV and job parsing
- GitHub project selection
- tailored summary generation
- cover letter generation
- PDF resume export
- cover letter export as `txt`, `tex`, or `pdf` depending on the flow

### LLM usage
The LLM is not used everywhere.

It is currently used for:
- reranking GitHub projects when `use_llm=true`
- generating the cover letter when `use_llm=true`
- reranking some PhD offers after embedding-based pre-ranking

The rest of the pipeline is rule-based, parser-based, and deterministic.

### PhD discovery
Currently integrated sources:
- `doctorat.gouv.fr`
- `ANRT CIFRE` through an authenticated session

PhD discovery currently includes:
- collection from the selected source
- offer normalization
- embedding + lexical scoring
- conditional LLM reranking when the initial signal is strong enough
- exclusion of offers marked as `Already applied`

### Source integration copilot
A V1 is available in the UI:
- create a source
- open a chat session
- inspect a URL
- propose a strategy (`public_api`, `authenticated_json`, etc.)
- activate the source

This copilot is constrained and deterministic. It is not yet a free-form agent with all development tools.

## Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Docker Compose
- Hugging Face Router / Inference API
- Tectonic for LaTeX compilation
- HTML/CSS/JS UI served by the backend

## Project structure

```text
app/
  core/                 config, DB, security
  dependencies/         FastAPI auth dependencies
  models/               SQLAlchemy tables
  routers/              API endpoints
  schemas/              Pydantic schemas
  services/             business logic
  ui/                   web interface
tests/                  targeted checks
docker-compose.yml
DOCKERFILE
Makefile
```

Important files:
- [app/main.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/main.py)
- [app/services/tailoring_engine.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/services/tailoring_engine.py)
- [app/services/doctorat_gouv_service.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/services/doctorat_gouv_service.py)
- [app/services/anrt_cifre_service.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/services/anrt_cifre_service.py)
- [app/services/source_agent.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/services/source_agent.py)
- [app/ui/index.html](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/ui/index.html)

## Requirements

- Docker
- Docker Compose

Optional but recommended:
- a Hugging Face token for LLM and embedding calls

## Environment variables

The project loads its environment from `.env`.

Important variables currently used in the project:
- `DATABASE_URL`
- `JWT_SECRET`
- `HF_TOKEN`
- `GEN_MODEL`
- `GEN_FALLBACK_MODEL`
- `TEI_MODEL`
- `ANRT_CIFRE_EMAIL`
- `ANRT_CIFRE_PASSWORD`

Examples:
- `HF_TOKEN` is required for embeddings and LLM calls
- `ANRT_CIFRE_EMAIL` / `ANRT_CIFRE_PASSWORD` are required for the authenticated ANRT source

## Run the project

```bash
docker compose up -d --build
```

Exposed services:
- backend: `http://localhost:8000`
- UI: `http://localhost:8000/ui`
- pgAdmin: `http://localhost:5050`

Stop everything:

```bash
docker compose down
```

## Quick usage

### 1. Create an account
From the UI:
- email
- full name
- password
- master CV
- optional GitHub username
- optional master cover letter

### 2. Load a profile
Once logged in:
- a LaTeX CV can be compiled and previewed
- the profile can be used for tailoring and PhD discovery

### 3. Create a job
In the `Job` section:
- enter a title
- paste a job description
- save it

### 4. Run tailoring
In the `Tailoring` section:
- choose `job_posting_id`
- choose the output language
- enable or disable `use_llm`

Typical outputs:
- tailored summary
- selected projects
- cover letter
- `pdf_path`
- `cover_letter_path`

### 5. Search for PhD opportunities
In the `Find theses` section:
- choose the source
- run the search
- import an offer as a job
- check `Already applied` to exclude it from future searches

### 6. Add a source
In the `Sources` section:
- create a source
- open the chat
- send a URL or type `inspect`
- type `activate` when the proposed strategy looks correct

## Currently supported PhD sources

### doctorat.gouv.fr
Strategy:
- public API

Observed flow:
- collection through `app.doctorat.gouv.fr/api`
- normalized field mapping
- embedding + lexical scoring

### ANRT CIFRE
Strategy:
- authenticated session
- DataTables JSON endpoint

Observed flow:
- login through HTML form
- listing through `/espace-membre/offre/dtList`
- details through `/espace-membre/offre/detail/{crypt}`

## Main API

### Auth
- `POST /auth/register`
- `POST /auth/login`

### Profiles
- `GET /profiles/`
- `POST /profiles/`
- `GET /profiles/{profile_id}`
- `PATCH /profiles/{profile_id}`
- `DELETE /profiles/{profile_id}`
- `GET /profiles/{profile_id}/compiled-pdf`

### Jobs
- `GET /jobs/`
- `POST /jobs/`
- `GET /jobs/{job_id}`
- `PATCH /jobs/{job_id}`
- `DELETE /jobs/{job_id}`

### GitHub
- `GET /github/validate`
- `POST /github/fetch`

### Tailoring
- `POST /tailoring/run`

### Exports
- `GET /exports/pdf`
- `GET /exports/pdf-inline`
- `GET /exports/docx`
- `GET /exports/letter`

### Thesis discovery
- `POST /thesis-discovery/search`
- `POST /thesis-discovery/import`
- `POST /thesis-discovery/applied`

### Source integration assistant
- `GET /thesis-sources/`
- `POST /thesis-sources/`
- `POST /source-agent/sessions`
- `GET /source-agent/sessions/{session_id}`
- `POST /source-agent/sessions/{session_id}/messages`

## Cover letter generation logic

Two modes are currently available.

### Without LLM
- template-based generation in [resume_generator.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/services/resume_generator.py)

### With LLM
- text generation in [llm_cover_letter.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/services/llm_cover_letter.py)
- reuse of the master cover letter when available
- neutral salutation or job-derived salutation when explicitly detected
- preservation of the paragraph count from the master template
- when a master LaTeX template exists, the generated text is injected into that template and compiled to PDF

## Thesis ranking logic

Current pipeline:
1. build a research intent from the CV
2. collect offers from the selected source
3. compute profile/offer embeddings
4. compute final score from semantic + lexical signals
5. run LLM reranking only when the initial signal is strong enough
6. filter out offers already marked as applied

Main implementation file:
- [doctorat_gouv_service.py](/home/cheikh/Desktop/levelUp/CV_TAILOR/app/services/doctorat_gouv_service.py)

## Tests

The project currently contains targeted checks around cover-letter behavior:

```bash
make test
```

or

```bash
make test-cover-letter
```

These commands run:

```bash
docker compose exec -T backend python - < tests/run_cover_letter_checks.py
```

## Current limitations

- the UI is intentionally simple
- the source copilot is a guided V1, not a fully autonomous agent
- thesis ranking quality still depends heavily on the signal available in the CV
- the ANRT source depends on valid credentials and on a third-party HTML/JSON structure that may change
- PDF upload at registration is still not implemented for actual extraction

## Suggested next steps

Natural future improvements:
- improve the user research intent extraction
- add more academic sources
- make the source copilot more autonomous
- persist richer inspection results
- improve error handling and source status visibility in the UI

## License

No license is currently declared in this repository.
