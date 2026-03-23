.PHONY: test test-cover-letter

test:
	docker compose exec -T backend python - < tests/run_cover_letter_checks.py

test-cover-letter:
	docker compose exec -T backend python - < tests/run_cover_letter_checks.py
