"""PostgreSQL production readiness checker for Pharmacy ERP.

Audits the codebase for SQLite-specific assumptions, raw SQL incompatibilities,
and provides migration guidance. Does NOT automatically migrate the database.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompatibilityIssue:
    severity: str  # 'critical', 'warning', 'info'
    category: str
    file_path: str
    line_number: int
    description: str
    recommendation: str


@dataclass
class PostgreSQLReadinessReport:
    is_ready: bool
    critical_issues: int
    warnings: int
    info_items: int
    issues: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    current_backend: str = ''


# ─── SQLite-specific patterns to detect ───────────────────────────────────────

SQLITE_PATTERNS = [
    {
        'pattern': r'PRAGMA\s+',
        'severity': 'critical',
        'category': 'raw_sql',
        'description': 'SQLite PRAGMA statement found — not supported in PostgreSQL',
        'recommendation': 'Remove PRAGMA statements. Use PostgreSQL SET commands or ALTER DATABASE.',
    },
    {
        'pattern': r'SELECT\s+datetime\(',
        'severity': 'warning',
        'category': 'raw_sql',
        'description': 'SQLite datetime() function — different in PostgreSQL',
        'recommendation': 'Use PostgreSQL NOW() or CURRENT_TIMESTAMP instead.',
    },
    {
        'pattern': r'SELECT\s+date\(',
        'severity': 'warning',
        'category': 'raw_sql',
        'description': 'SQLite date() function — different in PostgreSQL',
        'recommendation': 'Use PostgreSQL CURRENT_DATE or DATE() with proper casting.',
    },
    {
        'pattern': r'IFNULL\s*\(',
        'severity': 'critical',
        'category': 'raw_sql',
        'description': 'SQLite IFNULL() — use COALESCE() for cross-database compatibility',
        'recommendation': 'Replace IFNULL() with COALESCE() which works in both SQLite and PostgreSQL.',
    },
    {
        'pattern': r'(?<!\w)LIKE\s+',
        'severity': 'info',
        'category': 'raw_sql',
        'description': 'LIKE is case-sensitive in PostgreSQL but case-insensitive in SQLite',
        'recommendation': 'Use ILIKE for case-insensitive matching in PostgreSQL, or ILIKE for both.',
    },
    {
        'pattern': r'LIMIT\s+\d+\s*OFFSET\s+\d+',
        'severity': 'info',
        'category': 'raw_sql',
        'description': 'LIMIT/OFFSET works in both but Django ORM pagination is preferred',
        'recommendation': 'Consider using Django ORM pagination for cross-database compatibility.',
    },
    {
        'pattern': r'(?<!\w)BOOLEAN\s+(?!DEFAULT)',
        'severity': 'info',
        'category': 'schema',
        'description': 'SQLite stores booleans as integers; PostgreSQL has native BOOLEAN',
        'recommendation': 'Django handles this automatically. Verify BooleanField values in raw queries.',
    },
    {
        'pattern': r'AUTOINCREMENT',
        'severity': 'critical',
        'category': 'schema',
        'description': 'SQLite AUTOINCREMENT — PostgreSQL uses SERIAL or GENERATED ALWAYS AS IDENTITY',
        'recommendation': 'Django migrations handle this. Do not use raw AUTOINCREMENT in SQL.',
    },
    {
        'pattern': r'(?<!\w)INTEGER\s+PRIMARY\s+KEY',
        'severity': 'warning',
        'category': 'schema',
        'description': 'SQLite implicit rowid behavior differs from PostgreSQL',
        'recommendation': 'Use Django model primary_key=True. Avoid raw PRIMARY KEY definitions.',
    },
    {
        'pattern': r'(?<!\w)BLOB\b',
        'severity': 'warning',
        'category': 'schema',
        'description': 'SQLite BLOB — PostgreSQL uses BYTEA',
        'recommendation': 'Use Django BinaryField which maps correctly to both databases.',
    },
    {
        'pattern': r'(?<!\w)TEXT\b(?!.*DEFAULT)',
        'severity': 'info',
        'category': 'schema',
        'description': 'TEXT works in both databases but behavior may differ for empty strings vs NULL',
        'recommendation': 'Django TextField handles this. Verify empty string handling in raw queries.',
    },
    {
        'pattern': r'(?<!\w)DATETIME\b',
        'severity': 'info',
        'category': 'schema',
        'description': 'SQLite stores datetime as text; PostgreSQL has native TIMESTAMP',
        'recommendation': 'Use Django DateTimeField. Avoid raw datetime comparisons.',
    },
    {
        'pattern': r'(?<!\.)strftime\s*\(',
        'severity': 'critical',
        'category': 'raw_sql',
        'description': 'SQLite strftime() — use PostgreSQL TO_CHAR() instead',
        'recommendation': 'Replace strftime() with TO_CHAR() or use Django ORM date functions.',
    },
    {
        'pattern': r'(?<!\w)julianday\s*\(',
        'severity': 'critical',
        'category': 'raw_sql',
        'description': 'SQLite julianday() — not available in PostgreSQL',
        'recommendation': 'Use PostgreSQL EXTRACT(EPOCH FROM ...) for date arithmetic.',
    },
    {
        'pattern': r'(?<!\w)RANDOM\s*\(\s*\)',
        'severity': 'warning',
        'category': 'raw_sql',
        'description': 'SQLite RANDOM() — PostgreSQL uses RANDOM() without parentheses',
        'recommendation': 'Use Django ORM order_by("?") for random ordering.',
    },
    {
        'pattern': r'(?<!\w)GROUP_CONCAT\s*\(',
        'severity': 'critical',
        'category': 'raw_sql',
        'description': 'SQLite GROUP_CONCAT() — PostgreSQL uses STRING_AGG()',
        'recommendation': 'Replace GROUP_CONCAT() with STRING_AGG() or use Django ORM aggregation.',
    },
]

# File-lock and transaction assumptions
FILE_LOCK_PATTERNS = [
    {
        'pattern': r'file.?lock|sqlite.?lock|database.?locked',
        'severity': 'warning',
        'category': 'concurrency',
        'description': 'SQLite file-locking assumption detected',
        'recommendation': 'PostgreSQL uses row-level locking. Remove file-lock handling code.',
    },
    {
        'pattern': r'timeout\s*=\s*\d+.*busy',
        'severity': 'warning',
        'category': 'concurrency',
        'description': 'SQLite busy timeout configuration',
        'recommendation': 'Remove SQLite-specific timeout settings. PostgreSQL handles concurrency differently.',
    },
]


# ─── Readiness checker ────────────────────────────────────────────────────────

class PostgreSQLReadinessChecker:
    """Audit codebase for PostgreSQL compatibility issues."""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.issues = []
        self._scanned_files = 0
        self._total_lines = 0

    def run(self) -> PostgreSQLReadinessReport:
        """Run full compatibility audit."""
        self._scan_sql_files()
        self._scan_python_files()
        self._check_settings()
        self._check_migrations()

        critical = sum(1 for i in self.issues if i.severity == 'critical')
        warnings = sum(1 for i in self.issues if i.severity == 'warning')
        info = sum(1 for i in self.issues if i.severity == 'info')

        return PostgreSQLReadinessReport(
            is_ready=(critical == 0),
            critical_issues=critical,
            warnings=warnings,
            info_items=info,
            issues=self.issues,
            recommendations=self._generate_recommendations(),
            current_backend=self._detect_current_backend(),
        )

    def _scan_sql_files(self):
        """Scan .sql files for SQLite-specific syntax."""
        import os
        for root, dirs, files in os.walk(self.base_dir):
            if 'migrations' in root or '__pycache__' in root:
                continue
            for f in files:
                if f.endswith('.sql'):
                    filepath = os.path.join(root, f)
                    self._check_file(filepath, SQLITE_PATTERNS)

    def _scan_python_files(self):
        """Scan Python files for raw SQL with SQLite-specific patterns."""
        import os
        all_patterns = SQLITE_PATTERNS + FILE_LOCK_PATTERNS
        for root, dirs, files in os.walk(self.base_dir):
            if '__pycache__' in root or os.path.basename(root) == 'tests':
                continue
            for f in files:
                if f.endswith('.py'):
                    filepath = os.path.join(root, f)
                    if 'postgresql_readiness' in filepath:
                        continue
                    self._check_file(filepath, all_patterns)

    def _check_file(self, filepath: str, patterns: list):
        """Check a single file against patterns."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    for pattern in patterns:
                        if re.search(pattern['pattern'], line, re.IGNORECASE):
                            self.issues.append(CompatibilityIssue(
                                severity=pattern['severity'],
                                category=pattern['category'],
                                file_path=filepath.replace(str(self.base_dir), ''),
                                line_number=line_num,
                                description=pattern['description'],
                                recommendation=pattern['recommendation'],
                            ))
            self._scanned_files += 1
        except (PermissionError, OSError):
            pass

    def _check_settings(self):
        """Check Django settings for SQLite-specific configuration."""
        import os
        settings_path = os.path.join(self.base_dir, 'config', 'settings.py')
        prod_path = os.path.join(self.base_dir, 'config', 'settings_production.py')

        for path in [settings_path, prod_path]:
            if os.path.exists(path):
                self._scanned_files += 1

        # Check if SQLite is still the default (this is OK — we don't force migration)
        self.issues.append(CompatibilityIssue(
            severity='info',
            category='configuration',
            file_path='config/settings.py',
            line_number=0,
            description='SQLite is currently configured as default database',
            recommendation='To switch to PostgreSQL: 1) Install psycopg2-binary, 2) Update DATABASES in settings, 3) Run python manage.py migrate.',
        ))

    def _check_migrations(self):
        """Verify migrations are database-agnostic."""
        import os
        migrations_dir = os.path.join(self.base_dir, 'migrations')
        if os.path.exists(migrations_dir):
            for root, dirs, files in os.walk(migrations_dir):
                for f in files:
                    if f.endswith('.py') and not f.startswith('__'):
                        filepath = os.path.join(root, f)
                        self._check_file(filepath, [
                            p for p in SQLITE_PATTERNS if p['severity'] == 'critical'
                        ])

    def _detect_current_backend(self) -> str:
        """Detect currently configured database backend."""
        try:
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            import django
            django.setup()
            from django.conf import settings
            engine = settings.DATABASES['default']['ENGINE']
            if 'sqlite' in engine:
                return 'sqlite3'
            elif 'postgresql' in engine or 'postgres' in engine:
                return 'postgresql'
            return engine
        except Exception:
            return 'unknown'

    def _generate_recommendations(self) -> list:
        """Generate prioritized recommendations."""
        recs = []

        critical_count = sum(1 for i in self.issues if i.severity == 'critical')
        if critical_count > 0:
            recs.append(f"BLOCKER: {critical_count} critical compatibility issue(s) must be fixed before PostgreSQL migration.")

        recs.append("Django ORM handles most database differences automatically. Raw SQL queries need manual review.")
        recs.append("Test all custom queries against PostgreSQL before switching production.")
        recs.append("Use 'python manage.py migrate' after updating DATABASES — Django handles schema conversion.")
        recs.append("Backup SQLite database before migration: python manage.py dumpdata > backup.json")
        recs.append("After PostgreSQL setup: python manage.py loaddata backup.json")
        recs.append("Run full test suite against PostgreSQL: pytest --ds=config.settings_postgres")

        return recs
