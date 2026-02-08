from __future__ import annotations

from django.db import migrations, models


def backfill_mit_agreements(apps, schema_editor):
    Problem = apps.get_model("community", "Problem")
    ProblemAgreement = apps.get_model("community", "ProblemAgreement")
    DEFAULT_MIT_TEXT = """Permission is hereby granted, free of charge, to any person obtaining a copy
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

    problems = Problem.objects.all().only("id")
    for problem in problems:
        has_active = ProblemAgreement.objects.filter(problem=problem, is_active=True).exists()
        if has_active:
            continue
        ProblemAgreement.objects.create(
            problem=problem,
            text=DEFAULT_MIT_TEXT,
            license_spdx="MIT",
            version="1.0",
            is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0002_problem_status_and_likes"),
    ]

    operations = [
        migrations.AddField(
            model_name="problemagreement",
            name="license_spdx",
            field=models.CharField(default="MIT", max_length=32),
        ),
        migrations.AddField(
            model_name="problemagreement",
            name="version",
            field=models.CharField(default="1.0", max_length=16),
        ),
        migrations.RunPython(backfill_mit_agreements, migrations.RunPython.noop),
    ]
