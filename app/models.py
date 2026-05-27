from app.extensions import db


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.String, nullable=False, default="")


class Screen(db.Model):
    __tablename__ = "screens"

    id = db.Column(db.Integer, primary_key=True)
    screen_type = db.Column(db.String, nullable=False)
    config = db.Column(db.JSON, nullable=False, default=dict)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    position = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "screen_type": self.screen_type,
            "config": self.config or {},
            "enabled": self.enabled,
            "position": self.position,
        }

    @property
    def display_path(self) -> str:
        return f"/screen/{self.id}"
