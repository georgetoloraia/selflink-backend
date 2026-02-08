from __future__ import annotations

from django.utils import timezone

from apps.users.models import User

from apps.community.models import Problem, ProblemAgreement, ProblemEvent

MIT_LICENSE_TEXT = """Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def emit_problem_event(*, problem: Problem, actor: User | None, type: str, metadata: dict | None = None) -> ProblemEvent:
    event = ProblemEvent.objects.create(
        problem=problem,
        actor=actor,
        type=type,
        metadata=metadata or {},
    )
    Problem.objects.filter(pk=problem.pk).update(last_activity_at=timezone.now())
    return event


def ensure_active_agreement(problem: Problem) -> ProblemAgreement:
    active = (
        ProblemAgreement.objects.filter(problem=problem, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if active:
        return active
    agreement, _ = ProblemAgreement.objects.get_or_create(
        problem=problem,
        is_active=True,
        defaults={
            "text": MIT_LICENSE_TEXT,
            "license_spdx": "MIT",
            "version": "1.0",
        },
    )
    return agreement
