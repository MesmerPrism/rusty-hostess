using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

static partial class WpfCompanionTests
{
    public static void ProjectRunnerProjectionIsReadOnlyAndCompletionBound()
    {
        var repoRoot = LocateHostessRepoRoot();
        var fixture = Path.Combine(
            repoRoot.FullName,
            "fixtures",
            "project-runner",
            "valid",
            "operator-projection.json");
        var projection = HostessctlProjectRunnerService.LoadValidatedProjectionAsync(
                fixture,
                CancellationToken.None)
            .GetAwaiter()
            .GetResult();

        Assert(projection.Status == "complete", "WPF projection must require complete status");
        Assert(projection.DryRun && !projection.Executed,
            "WPF projection must remain explicitly read-only and unexecuted");
        Assert(projection.ProductLockRevision == 1,
            "WPF projection must preserve the selected product-lock revision");
        Assert(projection.Rows.Any(row => row.Kind == "closure" && row.Status == "pass"),
            "WPF projection must expose the exact closure row");
    }

    public static void ProjectRunnerProjectionRejectsExecutedOrIncompleteArtifacts()
    {
        var repoRoot = LocateHostessRepoRoot();
        var source = Path.Combine(
            repoRoot.FullName,
            "fixtures",
            "project-runner",
            "valid",
            "operator-projection.json");
        var temporary = Path.Combine(Path.GetTempPath(), $"hostess-project-runner-{Guid.NewGuid():N}.json");
        try
        {
            var damaged = File.ReadAllText(source)
                .Replace("\"executed\": false", "\"executed\": true", StringComparison.Ordinal);
            File.WriteAllText(temporary, damaged);
            var rejected = false;
            try
            {
                HostessctlProjectRunnerService.LoadValidatedProjectionAsync(
                        temporary,
                        CancellationToken.None)
                    .GetAwaiter()
                    .GetResult();
            }
            catch (InvalidOperationException)
            {
                rejected = true;
            }
            Assert(rejected, "WPF must reject a projection that claims execution");
        }
        finally
        {
            File.Delete(temporary);
        }
    }

    public static void ProjectRunnerOperatorActionMatchesReadOnlyCliRoute()
    {
        var action = OperatorActionCatalog.All.Single(
            row => row.ActionId == "wpf.project_runner.inspect");
        Assert(action.UiCommandProperty == "LoadProjectRunnerCommand",
            "project-runner action must map to the WPF load command");
        Assert(action.CliRoute.Contains(
                "project-runner inspect --completion $ProjectRunnerCompletion --out $ProjectRunnerProjection",
                StringComparison.Ordinal),
            "project-runner WPF action must expose the CLI-equivalent inspect route");
        Assert(!action.MutatesHost && !action.MutatesDevice && !action.RequiresQuestLease,
            "project-runner inspection must remain read-only and device-independent");
        Assert(action.EvidenceArtifact == "rusty.hostess.project_runner.projection.v1",
            "project-runner action must name the projected receipt artifact");
    }
}
