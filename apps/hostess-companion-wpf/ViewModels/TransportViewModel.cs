using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class TransportViewModel
{
    public TransportViewModel(TransportCapabilityDescriptor descriptor)
    {
        TransportId = descriptor.TransportId;
        Title = descriptor.Title;
        Family = descriptor.Family;
        Plane = descriptor.Plane;
        Delivery = descriptor.Delivery;
        PayloadRate = descriptor.PayloadRate;
        AuthorityRole = descriptor.AuthorityRole;
        Routes = Join(descriptor.RouteIds);
        EvidenceStages = Join(descriptor.RequiredEvidenceStages);
        SuitableFor = Join(descriptor.SuitableFor);
        Strengths = Join(descriptor.Strengths);
        Costs = Join(descriptor.Costs);
        SourcePath = descriptor.SourcePath;
    }

    public string TransportId { get; }

    public string Title { get; }

    public string Family { get; }

    public string Plane { get; }

    public string Delivery { get; }

    public string PayloadRate { get; }

    public string AuthorityRole { get; }

    public string Routes { get; }

    public string EvidenceStages { get; }

    public string SuitableFor { get; }

    public string Strengths { get; }

    public string Costs { get; }

    public string SourcePath { get; }

    public string StatusLine => $"{Family} / {Plane} / {Delivery}";

    public string DetailText =>
        $"Id: {TransportId}{Environment.NewLine}" +
        $"Family: {Family}{Environment.NewLine}" +
        $"Plane: {Plane}{Environment.NewLine}" +
        $"Delivery: {Delivery}{Environment.NewLine}" +
        $"Payload rate: {PayloadRate}{Environment.NewLine}" +
        $"Authority role: {AuthorityRole}{Environment.NewLine}" +
        $"Routes: {Routes}{Environment.NewLine}" +
        $"Required evidence: {EvidenceStages}{Environment.NewLine}" +
        $"Suitable for: {SuitableFor}{Environment.NewLine}" +
        $"Strengths: {Strengths}{Environment.NewLine}" +
        $"Costs: {Costs}{Environment.NewLine}" +
        $"Source: {SourcePath}";

    public Brush StatusBrush => Plane switch
    {
        "media" => Brushes.SteelBlue,
        "command" => Brushes.DarkSlateGray,
        _ => Brushes.DarkGreen,
    };

    private static string Join(IEnumerable<string> values) => string.Join(", ", values);
}
