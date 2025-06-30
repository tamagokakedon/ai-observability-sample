# Task 04: Recipe Detection and Ingredient Extraction

## Overview
Implement AI-powered recipe detection and ingredient extraction using Amazon Bedrock.

## Requirements
- Create RecipeDetectorService to analyze web page content
- Implement recipe classification (is this a recipe page?)
- Extract ingredients list from recipe content
- Support both Japanese and English content

## Key Features
- Binary classification: recipe vs non-recipe content
- Structured ingredient extraction with quantities and units
- Multi-language support (Japanese/English)
- Confidence scoring for detection results
- Fallback parsing for edge cases

## Implementation Details
- Use LangChain with Bedrock integration
- Create optimized prompts for recipe detection
- Implement structured output parsing
- Add caching for repeated URLs (1 hour TTL)
- Include confidence thresholds and validation

## Prompts to Implement
- Recipe detection prompt
- Ingredient extraction prompt
- Multi-language handling prompts

## Deliverables
- [ ] RecipeDetectorService class implemented
- [ ] Recipe classification functionality
- [ ] Ingredient extraction with structured output
- [ ] Multi-language prompt support
- [ ] Result caching implementation
- [ ] Confidence scoring and validation