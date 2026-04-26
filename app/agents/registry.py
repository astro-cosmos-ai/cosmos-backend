"""Maps section names to their context builders and system prompts."""
from app.agents.prompts import (
    personality, career, marriage,
    mind, skills, wealth, foreign, romance, business,
    property, health, education, parents, siblings, children, spirituality,
)
from app.services.harness.context_builder import (
    build_personality_context,
    build_career_context,
    build_marriage_context,
    build_mind_context,
    build_skills_context,
    build_wealth_context,
    build_foreign_context,
    build_romance_context,
    build_business_context,
    build_property_context,
    build_health_context,
    build_education_context,
    build_parents_context,
    build_siblings_context,
    build_children_context,
    build_spirituality_context,
)

AGENT_REGISTRY: dict[str, dict] = {
    "personality": {
        "context_builder": build_personality_context,
        "system_prompt": personality.SYSTEM_PROMPT,
    },
    "career": {
        "context_builder": build_career_context,
        "system_prompt": career.SYSTEM_PROMPT,
    },
    "marriage": {
        "context_builder": build_marriage_context,
        "system_prompt": marriage.SYSTEM_PROMPT,
    },
    "mind": {
        "context_builder": build_mind_context,
        "system_prompt": mind.SYSTEM_PROMPT,
    },
    "skills": {
        "context_builder": build_skills_context,
        "system_prompt": skills.SYSTEM_PROMPT,
    },
    "wealth": {
        "context_builder": build_wealth_context,
        "system_prompt": wealth.SYSTEM_PROMPT,
    },
    "foreign": {
        "context_builder": build_foreign_context,
        "system_prompt": foreign.SYSTEM_PROMPT,
    },
    "romance": {
        "context_builder": build_romance_context,
        "system_prompt": romance.SYSTEM_PROMPT,
    },
    "business": {
        "context_builder": build_business_context,
        "system_prompt": business.SYSTEM_PROMPT,
    },
    "property": {
        "context_builder": build_property_context,
        "system_prompt": property.SYSTEM_PROMPT,
    },
    "health": {
        "context_builder": build_health_context,
        "system_prompt": health.SYSTEM_PROMPT,
    },
    "education": {
        "context_builder": build_education_context,
        "system_prompt": education.SYSTEM_PROMPT,
    },
    "parents": {
        "context_builder": build_parents_context,
        "system_prompt": parents.SYSTEM_PROMPT,
    },
    "siblings": {
        "context_builder": build_siblings_context,
        "system_prompt": siblings.SYSTEM_PROMPT,
    },
    "children": {
        "context_builder": build_children_context,
        "system_prompt": children.SYSTEM_PROMPT,
    },
    "spirituality": {
        "context_builder": build_spirituality_context,
        "system_prompt": spirituality.SYSTEM_PROMPT,
    },
}


def get_agent_config(section: str) -> dict | None:
    return AGENT_REGISTRY.get(section)
