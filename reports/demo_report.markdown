# Evaluation Report — offline-demo

*Generated: 2026-10-18T12:10:55+00:00*

## Reproducibility

- Dataset: TEB v1.0.0 (content hash `ca6b0c19e1fbc1b4`, 160 examples)
- Provider: **mock** · Model: **teb-mock-v1**
- Prompt version: `prompt-v1` · Rubric version: `rubric-v1`
- Code version: `9ec05af`
- Job status: completed · Cost: $0.0000
- Config: `{"categories": [], "dataset_version": "1.0.0", "include_judge": false, "judge_model": null, "judge_rubric_version": "rubric-v1", "max_examples": null, "max_tokens": 1024, "partition": null, "sampling_seed": 42, "temperature": 0.0, "terminology_consistency": {"concepts_seen": 93, "consistency_factor": 0.871, "unstable_concepts": {"application": ["\u0b9a\u0bc6\u0baf\u0bb2\u0bbf", "\u0baa\u0baf\u0ba9\u0bcd\u0baa\u0bbe\u0b9f\u0bc1"], "attach": ["\u0b87\u0ba3\u0bc8", "\u0b87\u0ba3\u0bc8\u0ba4\u0bcd\u0ba4"], "bridge": ["\u0baa\u0bbe\u0bb2", "\u0baa\u0bbe\u0bb2\u0bae\u0bcd"], "cache": ["\u0b87\u0b9f\u0bc8\u0baf\u0b95 \u0b9e\u0bbe\u0baa\u0b95", "\u0b87\u0b9f\u0bc8\u0baf\u0b95 \u0b9e\u0bbe\u0baa\u0b95\u0bae\u0bcd"], "deadline": ["deadline", "\u0b95\u0bbe\u0bb2\u0b95\u0bcd\u0b95\u0b9f\u0bcd\u0b9f", "\u0b95\u0bbe\u0bb2\u0b95\u0bcd\u0b95\u0b9f\u0bcd\u0b9f\u0bae\u0bcd"], "meeting": ["\u0b95\u0bc2\u0b9f\u0bcd\u0b9f", "\u0b95\u0bc2\u0b9f\u0bcd\u0b9f\u0bae\u0bcd"], "milk": ["\u0baa\u0bbe", "\u0baa\u0bbe\u0bb2\u0bcd"], "password": ["\u0b95\u0b9f\u0bb5\u0bc1\u0b9a\u0bcd\u0b9a\u0bca", "\u0b95\u0b9f\u0bb5\u0bc1\u0b9a\u0bcd\u0b9a\u0bca\u0bb2\u0bcd"], "payment": ["payment", "\u0b95\u0b9f\u0bcd\u0b9f\u0ba3", "\u0b95\u0b9f\u0bcd\u0b9f\u0ba3\u0bae\u0bcd"], "postponed": ["\u0ba4\u0bb3\u0bcd\u0bb3\u0bbf \u0bb5\u0bc8\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f", "\u0ba4\u0bb3\u0bcd\u0bb3\u0bbf \u0bb5\u0bc8\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0ba4\u0bc1"], "train": ["\u0bb0\u0baf\u0bbf", "\u0bb0\u0baf\u0bbf\u0bb2\u0bcd"], "\u0bb5\u0bcb\u0bb2\u0bcd\u0b9f\u0bcd": ["volt", "volts"]}}, "thresholds": {"pass": 0.7}, "weights": {"completeness": 0.05, "constraint_satisfaction": 0.15, "entity_number_preservation": 0.1, "script_validity": 0.05, "semantic_preservation": 0.45, "terminology_consistency": 0.2}}`

## Headline metrics

| Metric | n | Mean |
|---|---|---|
| Overall (weighted) | 160 | 0.8993 |
| **Semantic preservation** | 160 | 0.9038 |
| **Terminology consistency** | 72 | 0.7824 |

## Per-category overall score

| Category | n | Mean overall | Mean semantic | Mean terminology |
|---|---|---|---|---|
| ambiguity_context | 10 | 0.9409 | 0.9328 | 1.0000 |
| business_email | 10 | 0.8696 | 0.8665 | 0.8889 |
| code_mixed_understanding | 10 | 1.0000 | 1.0000 | 1.0000 |
| customer_support | 10 | 0.9272 | 0.9323 | 0.9000 |
| entities_numbers | 10 | 0.8337 | 0.8145 | 0.8571 |
| idiom_culture | 10 | 0.8622 | 0.8739 | 0.0000 |
| instruction_following | 10 | 0.8349 | 0.8642 | 0.0000 |
| language_switching | 10 | 0.9931 | 0.9926 | 1.0000 |
| long_context_multiturn | 10 | 0.9600 | 1.0000 | 0.3333 |
| register_formality | 10 | 0.8646 | 0.8581 | 0.5000 |
| romanized_transliteration | 10 | 0.8105 | 0.8031 | n/a |
| safety_critical | 10 | 0.9046 | 0.9435 | 0.6429 |
| summarization_rewriting | 10 | 0.7727 | 0.7785 | 0.5833 |
| technical_terminology | 10 | 0.9162 | 0.9100 | 0.9259 |
| translation_en_to_ta | 10 | 0.9479 | 0.9397 | 0.9444 |
| translation_ta_to_en | 10 | 0.9502 | 0.9504 | 1.0000 |

## Failure examples (38)

### TEB-T2E-0001
- Error: numeric_error: Number/date/unit altered or dropped; omission: Required fact or constraint missing
- Response: ```I am going to school at 9 o'clock today morning.```

### TEB-E2T-0005
- Error: omission: Required fact or constraint missing; terminology_miss: Glossary term not translated as specified
- Response: ```இந்த கோப்பைத் திறக்காதே.```

### TEB-E2T-0007
- Error: omission: Required fact or constraint missing
- Response: ```இந்த திட்டத்தை முடிக்க எங்களுக்கு கூடுதல் நேரம் தேவை.```

### TEB-ROM-0002
- Error: omission: Required fact or constraint missing; script_error: Wrong script for target language; transliteration_error: Romanization or Tamil-script rendering wrong
- Response: ```The model responded in an unrelated language. Response text here.```

### TEB-ROM-0004
- Error: omission: Required fact or constraint missing; script_error: Wrong script for target language; transliteration_error: Romanization or Tamil-script rendering wrong
- Response: ```The model responded in an unrelated language. Response text here.```

### TEB-ROM-0009
- Error: omission: Required fact or constraint missing; script_error: Wrong script for target language; transliteration_error: Romanization or Tamil-script rendering wrong
- Response: ```The model responded in an unrelated language. Response text here.```

### TEB-REG-0005
- Error: omission: Required fact or constraint missing
- Response: ```நீங்கள் கூட்டத்தில் கலந்து கொண்டால் நான் நன்றியடைவேன்.```

### TEB-REG-0009
- Error: omission: Required fact or constraint missing; terminology_miss: Glossary term not translated as specified
- Response: ```தயவுசெய்து இலவசக் கணக்கின் விவரங்களைப் பகிர்ந்து கொள்ள முடியுமா?```

### TEB-REG-0010
- Error: omission: Required fact or constraint missing
- Response: ```The model responded in an unrelated language. Response text here.```

### TEB-INS-0002
- Error: terminology_miss: Glossary term not translated as specified
- Response: ```1. சென்னை
2. கோயம்பத்தூர்
3. மதுரை
4. சேலம்
5. திருச்சிராப்பள்ளி```

---
_This report was generated from stored results. Automatic scores are deterministic proxies; they are not human judgments. See the methodology documentation for limitations._