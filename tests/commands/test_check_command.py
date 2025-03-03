import sys
from io import StringIO
from typing import List

import pytest

from commitizen import cli, commands, git
from commitizen.exceptions import (
    InvalidCommandArgumentError,
    InvalidCommitMessageError,
    NoCommitsFoundError,
)

COMMIT_LOG = [
    "refactor: A code change that neither fixes a bug nor adds a feature",
    r"refactor(cz/connventional_commit): use \S to check scope",
    "refactor(git): remove unnecessary dot between git range",
    "bump: version 1.16.3 → 1.16.4",
    (
        "Merge pull request #139 from Lee-W/fix-init-clean-config-file\n"
        "Fix init clean config file"
    ),
    "ci(pyproject.toml): add configuration for coverage",
    "fix(commands/init): fix clean up file when initialize commitizen config\n#138",
    "refactor(defaults): split config files into long term support and deprecated ones",
    "bump: version 1.16.2 → 1.16.3",
    (
        "Merge pull request #136 from Lee-W/remove-redundant-readme\n"
        "Remove redundant readme"
    ),
    "fix: replace README.rst with docs/README.md in config files",
    (
        "refactor(docs): remove README.rst and use docs/README.md\n"
        "By removing README.rst, we no longer need to maintain "
        "two document with almost the same content\n"
        "Github can read docs/README.md as README for the project."
    ),
    "docs(check): pin pre-commit to v1.16.2",
    "docs(check): fix pre-commit setup",
    "bump: version 1.16.1 → 1.16.2",
    "Merge pull request #135 from Lee-W/fix-pre-commit-hook\nFix pre commit hook",
    "docs(check): enforce cz check only whem committing",
    (
        'Revert "fix(pre-commit): set pre-commit check stage to commit-msg"\n'
        "This reverts commit afc70133e4a81344928561fbf3bb20738dfc8a0b."
    ),
    "feat!: add user stuff",
]


def _build_fake_git_commits(commit_msgs: List[str]) -> List[git.GitCommit]:
    return [git.GitCommit("test_rev", commit_msg) for commit_msg in commit_msgs]


def test_check_jira_fails(mocker):
    testargs = ["cz", "-n", "cz_jira", "check", "--commit-msg-file", "some_file"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch(
        "commitizen.commands.check.open",
        mocker.mock_open(read_data="random message for J-2 #fake_command blah"),
    )
    with pytest.raises(InvalidCommitMessageError) as excinfo:
        cli.main()
    assert "commit validation: failed!" in str(excinfo.value)


def test_check_jira_command_after_issue_one_space(mocker, capsys):
    testargs = ["cz", "-n", "cz_jira", "check", "--commit-msg-file", "some_file"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch(
        "commitizen.commands.check.open",
        mocker.mock_open(read_data="JR-23 #command some arguments etc"),
    )
    cli.main()
    out, _ = capsys.readouterr()
    assert "Commit validation: successful!" in out


def test_check_jira_command_after_issue_two_spaces(mocker, capsys):
    testargs = ["cz", "-n", "cz_jira", "check", "--commit-msg-file", "some_file"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch(
        "commitizen.commands.check.open",
        mocker.mock_open(read_data="JR-2  #command some arguments etc"),
    )
    cli.main()
    out, _ = capsys.readouterr()
    assert "Commit validation: successful!" in out


def test_check_jira_text_between_issue_and_command(mocker, capsys):
    testargs = ["cz", "-n", "cz_jira", "check", "--commit-msg-file", "some_file"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch(
        "commitizen.commands.check.open",
        mocker.mock_open(read_data="JR-234 some text #command some arguments etc"),
    )
    cli.main()
    out, _ = capsys.readouterr()
    assert "Commit validation: successful!" in out


def test_check_jira_multiple_commands(mocker, capsys):
    testargs = ["cz", "-n", "cz_jira", "check", "--commit-msg-file", "some_file"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch(
        "commitizen.commands.check.open",
        mocker.mock_open(read_data="JRA-23 some text #command1 args #command2 args"),
    )
    cli.main()
    out, _ = capsys.readouterr()
    assert "Commit validation: successful!" in out


def test_check_conventional_commit_succeeds(mocker, capsys):
    testargs = ["cz", "check", "--commit-msg-file", "some_file"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch(
        "commitizen.commands.check.open",
        mocker.mock_open(read_data="fix(scope): some commit message"),
    )
    cli.main()
    out, _ = capsys.readouterr()
    assert "Commit validation: successful!" in out


@pytest.mark.parametrize(
    "commit_msg",
    (
        "feat!(lang): removed polish language",
        "no conventional commit",
    ),
)
def test_check_no_conventional_commit(commit_msg, config, mocker, tmpdir):
    with pytest.raises(InvalidCommitMessageError):
        error_mock = mocker.patch("commitizen.out.error")

        tempfile = tmpdir.join("temp_commit_file")
        tempfile.write(commit_msg)

        check_cmd = commands.Check(
            config=config, arguments={"commit_msg_file": tempfile}
        )
        check_cmd()
        error_mock.assert_called_once()


@pytest.mark.parametrize(
    "commit_msg",
    (
        "feat(lang)!: removed polish language",
        "feat(lang): added polish language",
        "feat: add polish language",
        "bump: 0.0.1 -> 1.0.0",
    ),
)
def test_check_conventional_commit(commit_msg, config, mocker, tmpdir):
    success_mock = mocker.patch("commitizen.out.success")

    tempfile = tmpdir.join("temp_commit_file")
    tempfile.write(commit_msg)

    check_cmd = commands.Check(config=config, arguments={"commit_msg_file": tempfile})

    check_cmd()
    success_mock.assert_called_once()


def test_check_command_when_commit_file_not_found(config):
    with pytest.raises(FileNotFoundError):
        commands.Check(config=config, arguments={"commit_msg_file": "no_such_file"})()


def test_check_a_range_of_git_commits(config, mocker):
    success_mock = mocker.patch("commitizen.out.success")
    mocker.patch(
        "commitizen.git.get_commits", return_value=_build_fake_git_commits(COMMIT_LOG)
    )

    check_cmd = commands.Check(
        config=config, arguments={"rev_range": "HEAD~10..master"}
    )

    check_cmd()
    success_mock.assert_called_once()


def test_check_a_range_of_git_commits_and_failed(config, mocker):
    error_mock = mocker.patch("commitizen.out.error")
    mocker.patch(
        "commitizen.git.get_commits",
        return_value=_build_fake_git_commits(["This commit does not follow rule"]),
    )
    check_cmd = commands.Check(
        config=config, arguments={"rev_range": "HEAD~10..master"}
    )

    with pytest.raises(InvalidCommitMessageError):
        check_cmd()
        error_mock.assert_called_once()


def test_check_command_with_invalid_argment(config):
    with pytest.raises(InvalidCommandArgumentError) as excinfo:
        commands.Check(
            config=config,
            arguments={"commit_msg_file": "some_file", "rev_range": "HEAD~10..master"},
        )
    assert "One and only one argument is required for check command!" in str(
        excinfo.value
    )


def test_check_command_with_empty_range(config, mocker):
    check_cmd = commands.Check(config=config, arguments={"rev_range": "master..master"})
    with pytest.raises(NoCommitsFoundError) as excinfo:
        check_cmd()

    assert "No commit found with range: 'master..master'" in str(excinfo)


def test_check_a_range_of_failed_git_commits(config, mocker):
    ill_formated_commits_msgs = [
        "First commit does not follow rule",
        "Second commit does not follow rule",
        ("Third commit does not follow rule\n" "Ill-formatted commit with body"),
    ]
    mocker.patch(
        "commitizen.git.get_commits",
        return_value=_build_fake_git_commits(ill_formated_commits_msgs),
    )
    check_cmd = commands.Check(
        config=config, arguments={"rev_range": "HEAD~10..master"}
    )

    with pytest.raises(InvalidCommitMessageError) as excinfo:
        check_cmd()
    assert all([msg in str(excinfo.value) for msg in ill_formated_commits_msgs])


def test_check_command_with_valid_message(config, mocker):
    success_mock = mocker.patch("commitizen.out.success")
    check_cmd = commands.Check(
        config=config, arguments={"message": "fix(scope): some commit message"}
    )

    check_cmd()
    success_mock.assert_called_once()


def test_check_command_with_invalid_message(config, mocker):
    error_mock = mocker.patch("commitizen.out.error")
    check_cmd = commands.Check(config=config, arguments={"message": "bad commit"})

    with pytest.raises(InvalidCommitMessageError):
        check_cmd()
        error_mock.assert_called_once()


def test_check_command_with_pipe_message(mocker, capsys):
    testargs = ["cz", "check"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch("sys.stdin", StringIO("fix(scope): some commit message"))

    cli.main()
    out, _ = capsys.readouterr()
    assert "Commit validation: successful!" in out


def test_check_command_with_pipe_message_and_failed(mocker):
    testargs = ["cz", "check"]
    mocker.patch.object(sys, "argv", testargs)
    mocker.patch("sys.stdin", StringIO("bad commit message"))

    with pytest.raises(InvalidCommitMessageError) as excinfo:
        cli.main()
    assert "commit validation: failed!" in str(excinfo.value)
