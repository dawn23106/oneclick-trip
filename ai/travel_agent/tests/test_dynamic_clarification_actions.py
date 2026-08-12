from app.domain.models import ClarificationAction, ClarificationReply, TravelEntities
from app.graph.nodes.ask_user import _compose_patch


def _reply(actions: list[ClarificationAction]) -> ClarificationReply:
    return ClarificationReply(
        kicker="再选一下",
        title="同行人数",
        message="这次一共有几个人出发？",
        choice_prompt="选择人数",
        actions=actions,
    )


def test_model_actions_are_kept_inside_current_slot_contract() -> None:
    state = {"entities": TravelEntities(destination="成都"), "missing_fields": ["people"]}
    patch = _compose_patch(
        state,
        _reply(
            [
                ClarificationAction(id="two-people", field="people", label="两个人", message="一共两个人"),
                ClarificationAction(id="family-four", field="people", label="四人家庭", message="一共四个人"),
            ]
        ),
    )

    assert patch["clarification_reply"].choice_prompt == "选择人数"
    assert [item.id for item in patch["clarification_reply"].actions] == [
        "two-people",
        "family-four",
    ]


def test_out_of_contract_model_actions_use_code_fallback() -> None:
    state = {"entities": TravelEntities(destination="成都"), "missing_fields": ["people"]}
    patch = _compose_patch(
        state,
        _reply(
            [
                ClarificationAction(id="change-city", field="destination", label="去西安", message="我想去西安"),
                ClarificationAction(id="bad$id", field="people", label="两个人", message="一共两个人"),
            ]
        ),
    )

    assert patch["clarification_reply"].choice_prompt == "这次一共几个人出发？"
    assert [item.field for item in patch["clarification_reply"].actions] == [
        "people",
        "people",
        "people",
        "people",
    ]
