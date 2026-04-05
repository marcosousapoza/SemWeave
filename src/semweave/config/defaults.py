"""Default configuration values for SemWeave."""

from semweave.config.schema import (
    CommentStyle,
    FieldSpec,
    NodeSchema,
    SemWeaveConfig,
)

DEFAULT_CONFIG = SemWeaveConfig(
    comment_styles=[
        CommentStyle(prefix="%"),
        CommentStyle(prefix="<!--", suffix="-->"),
        CommentStyle(prefix="//"),
        CommentStyle(prefix="#"),
    ],
    annotation_prefix="mcp:",
    node_schema=NodeSchema(
        roles=["region", "section", "definition", "example", "theorem", "proof", "note", "code"],
        fields=[
            FieldSpec(name="role", required=True, type="str"),
            FieldSpec(name="name", required=False, type="str"),
            FieldSpec(name="anchors", required=False, type="list"),
        ],
    ),
)
