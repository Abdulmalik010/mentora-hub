# Diagnosis eval

Planted-flaw recall against samples/expected.json over live runs.
Strict recall = expected quote cited in a gap; category recall = flaw
category present among gaps.

| sample | mode | rep | strict | category | grounding | latency | tokens | gaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| thesis_excerpt_stats.pdf | parallel | 1 | 100% | 100% | 100% | 13.9s | 7860 | 10 |
| thesis_excerpt_stats.pdf | parallel | 2 | 67% | 100% | 100% | 14.3s | 7588 | 8 |
| thesis_excerpt_stats.pdf | parallel | 3 | 100% | 100% | 100% | 17.0s | 8966 | 9 |
| thesis_excerpt_stats.pdf | single | 1 | 0% | 100% | 100% | 29.1s | 3809 | 5 |
| thesis_excerpt_stats.pdf | single | 2 | 0% | 100% | 100% | 36.8s | 3275 | 4 |
| thesis_excerpt_stats.pdf | single | 3 | 0% | 100% | 100% | 41.7s | 3644 | 4 |
| thesis_excerpt_methods.docx | parallel | 1 | 100% | 100% | 100% | 11.3s | 6999 | 11 |
| thesis_excerpt_methods.docx | parallel | 2 | 100% | 100% | 100% | 11.8s | 6670 | 11 |
| thesis_excerpt_methods.docx | parallel | 3 | 100% | 100% | 100% | 11.4s | 7269 | 11 |
| thesis_excerpt_methods.docx | single | 1 | 100% | 67% | 100% | 24.8s | 2759 | 5 |
| thesis_excerpt_methods.docx | single | 2 | 100% | 100% | 100% | 23.7s | 2511 | 5 |
| thesis_excerpt_methods.docx | single | 3 | 100% | 100% | 100% | 33.2s | 3226 | 5 |

## Means by mode

- parallel: strict 94%, category 100%, latency 13.3s, tokens 7559
- single: strict 50%, category 94%, latency 31.5s, tokens 3204
