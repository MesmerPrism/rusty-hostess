using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

static partial class WpfCompanionTests
{
    public static void ShellRecenterProjectsCallbackAndEffectSeparately()
    {
        var arguments = HostessctlShellRecenterService.BuildArguments("private-profile.json", "recenter", "report.json");
        Assert(arguments.SequenceEqual(new[] { "companion-session", "shell-recenter", "--profile", "private-profile.json", "--mode", "recenter", "--out", "report.json" }),
            "WPF must invoke the same typed CLI with the exact pinned profile");
        var report = new CompanionReportProjection
        {
            Rows = [
                new() { Kind = "shell_recenter", Label = "Original callback", Status = "pass", Evidence = "success", Details = JsonSerializer.SerializeToElement(new { state = "success" }) },
                new() { Kind = "shell_recenter", Label = "Observed effect", Status = "warn", Evidence = "unverified", Notes = "Independent wearer/reference-space observation required", Details = JsonSerializer.SerializeToElement(new { state = "unverified" }) },
                new() { Kind = "shell_recenter", Label = "Original retirement", Status = "warn", Evidence = "active", Details = JsonSerializer.SerializeToElement(new { state = "active", retired = false }) },
            ],
        };
        var page = new CommandsPageViewModel();
        page.ApplyShellRecenterProjection(report);
        Assert(page.Rows.Count == 3, "every source-owned shell stage must be visible");
        Assert(page.Rows[0].Status == "pass" && page.Rows[1].Status == "warn" && page.Rows[2].Status == "warn",
            "callback must not promote observed effect or original retirement");
        Assert(page.Rows[1].EvidenceRefs.Contains("unverified") && page.Rows[2].EvidenceRefs.Contains("false"),
            "WPF details must preserve the original source evidence");
        var action = OperatorActionCatalog.All.Single(row => row.ActionId == "wpf.command.shell_recenter");
        Assert(action.RequiresQuestLease && action.MutatesDevice && action.MutatesHost && !action.RequiresAdbServerLifecycleLease,
            "typed shell action must expose exact Quest custody without owning the shared ADB daemon");
    }
}
