"""Disabled legacy evaluation suite; its artifacts are not valid evidence."""

from eval import legacy_evaluation_disabled


def main() -> None:
    legacy_evaluation_disabled("Legacy evaluation suite")


if __name__ == "__main__":
    main()
