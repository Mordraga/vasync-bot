"""Turns a discord.py member into the identity headers the vasync-database
API needs (see that service's app/core/security.py)."""

from dataclasses import dataclass

import discord


@dataclass(frozen=True, slots=True)
class CallerIdentity:
    discord_id: int
    guild_id: int
    role_ids: set[int]

    def as_headers(self, service_token: str) -> dict[str, str]:
        return {
            "X-Service-Token": service_token,
            "X-Discord-User-Id": str(self.discord_id),
            "X-Discord-Guild-Id": str(self.guild_id),
            "X-Discord-Role-Ids": ",".join(str(role_id) for role_id in self.role_ids),
        }


def identity_from_member(member: discord.Member) -> CallerIdentity:
    return CallerIdentity(
        discord_id=member.id,
        guild_id=member.guild.id,
        role_ids={role.id for role in member.roles},
    )
