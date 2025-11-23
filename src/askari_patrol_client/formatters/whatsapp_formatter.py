"""
WhatsApp Message Formatter for Askari Patrol MCP Server

Formats API responses into WhatsApp-friendly messages using WhatsApp's
supported formatting: *bold*, _italic_, ~strikethrough~, ```monospace```
"""

from common.schemas import (
    CallLog,
    GetStatsResponse,
    LoginResponse,
    PaginatedResponse,
    PaginationMeta,
    Patrol,
    SecurityGuard,
    Shift,
    Site,
)


class WhatsAppFormatter:
    """Formats Askari Patrol API responses for WhatsApp messages."""

    # Emojis for visual clarity
    EMOJI = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "site": "📍",
        "guard": "👮",
        "patrol": "🚶",
        "shift": "🕐",
        "call": "📞",
        "stats": "📊",
        "company": "🏢",
        "calendar": "📅",
        "time": "⏰",
        "phone": "📱",
        "score": "⭐",
        "notification": "🔔",
        "page": "📄",
        "day": "☀️",
        "night": "🌙",
        "answered": "✅",
        "missed": "❌",
    }

    def _format_pagination(self, meta: PaginationMeta) -> str:
        """Format pagination info."""
        return (
            f"{self.EMOJI['page']} Page {meta['currentPage']} of {meta['totalPages']} "
            f"({meta['totalItems']} total)"
        )

    def _format_guard_name(self, guard: SecurityGuard | None) -> str:
        """Format security guard name."""
        if not guard:
            return "Unknown Guard"
        return f"{guard['firstName']} {guard['lastName']}"

    def _format_site_brief(self, site: Site) -> str:
        """Format site name briefly."""
        return site.get("name", "Unknown Site")

    def format_login_success(self, response: LoginResponse) -> str:
        """Format successful login response."""
        return (
            f"{self.EMOJI['success']} *Login Successful*\n\n"
            f"You are now authenticated and can access protected endpoints."
        )

    def format_login_error(self, error: str) -> str:
        """Format login error."""
        return f"{self.EMOJI['error']} *Login Failed*\n\nError: {error}"

    def format_token_set(self) -> str:
        """Format token set confirmation."""
        return f"{self.EMOJI['success']} *Authentication token set successfully*"

    def format_stats(self, stats: GetStatsResponse) -> str:
        """Format system statistics."""
        return (
            f"{self.EMOJI['stats']} *System Statistics*\n"
            f"{'─' * 20}\n\n"
            f"{self.EMOJI['company']} Companies: *{stats['companyCount']}*\n"
            f"{self.EMOJI['site']} Sites: *{stats['siteCount']}*\n"
            f"{self.EMOJI['guard']} Security Guards: *{stats['securityGuardCount']}*\n"
            f"👤 Company Admins: *{stats['companyAdminCount']}*\n"
            f"👤 Site Admins: *{stats['siteAdminCount']}*\n"
            f"🏷️ Tags: *{stats['tagCount']}*"
        )

    def format_site(self, site: Site) -> str:
        """Format a single site."""
        lines = [
            f"{self.EMOJI['site']} *{site['name']}*",
        ]

        if site.get("phoneNumber"):
            lines.append(f"   {self.EMOJI['phone']} {site['phoneNumber']}")

        if site.get("latitude") and site.get("longitude"):
            lines.append(f"   📌 {site['latitude']}, {site['longitude']}")

        if site.get("securityGuardCount"):
            lines.append(
                f"   {self.EMOJI['guard']} Guards: {site['securityGuardCount']}"
            )

        if site.get("requiredPatrolsPerGuard"):
            lines.append(
                f"   {self.EMOJI['patrol']} Required Patrols: {site['requiredPatrolsPerGuard']}/guard"
            )

        if site.get("patrolType"):
            lines.append(f"   📋 Patrol Type: {site['patrolType']}")

        if site.get("company"):
            lines.append(f"   {self.EMOJI['company']} {site['company']['name']}")

        if site.get("latestPatrol"):
            lines.append(f"   🕐 Last Patrol: {site['latestPatrol']}")

        return "\n".join(lines)

    def format_sites_list(self, response: PaginatedResponse[Site]) -> str:
        """Format paginated sites list."""
        if not response["data"]:
            return f"{self.EMOJI['warning']} No sites found."

        header = f"{self.EMOJI['site']} *Sites List*\n{'─' * 20}\n\n"
        sites = "\n\n".join(self.format_site(site) for site in response["data"])
        pagination = f"\n\n{'─' * 20}\n{self._format_pagination(response['meta'])}"

        return header + sites + pagination

    def format_shift(self, shift: Shift) -> str:
        """Format a single shift."""
        emoji = self.EMOJI["day"] if shift["type"] == "DAY" else self.EMOJI["night"]

        lines = [
            f"{emoji} *{shift['type']} Shift*",
            f"   {self.EMOJI['site']} {shift['site']['name']}",
        ]

        if shift.get("securityGuards"):
            guard_names = [self._format_guard_name(g) for g in shift["securityGuards"]]
            lines.append(f"   {self.EMOJI['guard']} Guards: {', '.join(guard_names)}")

        return "\n".join(lines)

    def format_shifts_list(self, shifts: list[Shift], site_name: str = "") -> str:
        """Format list of shifts."""
        if not shifts:
            return f"{self.EMOJI['warning']} No shifts found."

        header = f"{self.EMOJI['shift']} *Shifts*"
        if site_name:
            header += f" - {site_name}"
        header += f"\n{'─' * 20}\n\n"

        formatted = "\n\n".join(self.format_shift(shift) for shift in shifts)

        return header + formatted

    def format_patrol(self, patrol: Patrol) -> str:
        """Format a single patrol."""
        guard_name = self._format_guard_name(patrol.get("securityGuard"))

        lines = [
            f"{self.EMOJI['patrol']} *Patrol #{patrol['id']}*",
            f"   {self.EMOJI['calendar']} {patrol['date']}",
            f"   {self.EMOJI['time']} {patrol['startTime']}",
            f"   {self.EMOJI['guard']} {guard_name}",
            f"   {self.EMOJI['site']} {patrol['site']['name']}",
        ]

        return "\n".join(lines)

    def format_patrols_list(
        self, response: PaginatedResponse[Patrol], title: str = "Patrols"
    ) -> str:
        """Format paginated patrols list."""
        if not response["data"]:
            return f"{self.EMOJI['warning']} No patrols found."

        header = f"{self.EMOJI['patrol']} *{title}*\n{'─' * 20}\n\n"
        patrols = "\n\n".join(self.format_patrol(p) for p in response["data"])
        pagination = f"\n\n{'─' * 20}\n{self._format_pagination(response['meta'])}"

        return header + patrols + pagination

    def format_call_log(self, call: CallLog) -> str:
        """Format a single call log."""
        status_emoji = (
            self.EMOJI["answered"] if call["isAnswered"] else self.EMOJI["missed"]
        )
        status_text = "Answered" if call["isAnswered"] else "Missed"

        lines = [
            f"{self.EMOJI['call']} *Call #{call['id']}* {status_emoji}",
            f"   {self.EMOJI['calendar']} {call['date']}",
            f"   {self.EMOJI['time']} {call['time']}",
            f"   {self.EMOJI['site']} {call['site']['name']}",
            f"   📋 Status: {status_text}",
        ]

        if call.get("answeredBy"):
            name = f"{call['answeredBy']['firstName']} {call['answeredBy']['lastName']}"
            lines.append(f"   {self.EMOJI['guard']} Answered by: {name}")

        if call.get("response"):
            lines.append(f"   💬 Response: {call['response']}")

        return "\n".join(lines)

    def format_call_logs_list(self, response: PaginatedResponse[CallLog]) -> str:
        """Format paginated call logs list."""
        if not response["data"]:
            return f"{self.EMOJI['warning']} No call logs found."

        header = f"{self.EMOJI['call']} *Call Logs*\n{'─' * 20}\n\n"
        calls = "\n\n".join(self.format_call_log(c) for c in response["data"])
        pagination = f"\n\n{'─' * 20}\n{self._format_pagination(response['meta'])}"

        return header + calls + pagination

    def format_guard(self, guard: SecurityGuard) -> str:
        """Format a single security guard."""
        lines = [
            f"{self.EMOJI['guard']} *{guard['firstName']} {guard['lastName']}*",
            f"   🆔 ID: {guard['uniqueId']}",
            f"   {self.EMOJI['phone']} {guard['phoneNumber']}",
            f"   👤 Role: {guard['role']}",
            f"   📋 Type: {guard['type']}",
        ]

        if guard.get("gender"):
            lines.append(f"   ⚧ Gender: {guard['gender']}")

        if guard.get("dateOfBirth"):
            lines.append(f"   🎂 DOB: {guard['dateOfBirth']}")

        if guard.get("company"):
            lines.append(f"   {self.EMOJI['company']} {guard['company']['name']}")

        return "\n".join(lines)

    def format_guards_list(self, response: PaginatedResponse[SecurityGuard]) -> str:
        """Format paginated security guards list."""
        if not response["data"]:
            return f"{self.EMOJI['warning']} No security guards found."

        header = f"{self.EMOJI['guard']} *Security Guards*\n{'─' * 20}\n\n"
        guards = "\n\n".join(self.format_guard(g) for g in response["data"])
        pagination = f"\n\n{'─' * 20}\n{self._format_pagination(response['meta'])}"

        return header + guards + pagination

    def format_notification(self, notification: dict) -> str:
        """Format a single notification."""
        lines = [f"{self.EMOJI['notification']} *Notification*"]

        for key, value in notification.items():
            if value is not None:
                lines.append(f"   {key}: {value}")

        return "\n".join(lines)

    def format_notifications_list(self, response: PaginatedResponse[dict]) -> str:
        """Format paginated notifications list."""
        if not response["data"]:
            return f"{self.EMOJI['warning']} No notifications found."

        header = f"{self.EMOJI['notification']} *Notifications*\n{'─' * 20}\n\n"
        notifs = "\n\n".join(self.format_notification(n) for n in response["data"])
        pagination = f"\n\n{'─' * 20}\n{self._format_pagination(response['meta'])}"

        return header + notifs + pagination

    def format_monthly_score(
        self, score: str, site_name: str, year: int, month: int
    ) -> str:
        """Format monthly performance score."""
        month_names = [
            "",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        return (
            f"{self.EMOJI['score']} *Monthly Performance*\n"
            f"{'─' * 20}\n\n"
            f"{self.EMOJI['site']} Site: *{site_name}*\n"
            f"{self.EMOJI['calendar']} Period: *{month_names[month]} {year}*\n\n"
            f"📈 Score:\n```\n{score}\n```"
        )

    def format_error(self, error: str, context: str = "") -> str:
        """Format an error message."""
        msg = f"{self.EMOJI['error']} *Error*"
        if context:
            msg += f" - {context}"
        msg += f"\n\n{error}"
        return msg

    def format_auth_required(self) -> str:
        """Format authentication required message."""
        return (
            f"{self.EMOJI['warning']} *Authentication Required*\n\n"
            f"Please login first using the login command with your credentials."
        )
