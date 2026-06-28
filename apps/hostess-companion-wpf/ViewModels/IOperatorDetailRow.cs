using System.Windows.Media;

namespace HostessCompanion.Wpf.ViewModels;

public interface IOperatorDetailRow
{
    string Title { get; }

    string StatusLine { get; }

    string DetailText { get; }

    Brush StatusBrush { get; }
}
