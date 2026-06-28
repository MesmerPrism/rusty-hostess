using System.Collections.ObjectModel;
using System.Windows.Media;

namespace HostessCompanion.Wpf.ViewModels;

public class OperatorPageViewModel<TRow> : ObservableViewModel
    where TRow : class, IOperatorDetailRow
{
    private readonly string emptyDetailTitle;
    private TRow? selectedRow;

    public OperatorPageViewModel(string emptyDetailTitle)
    {
        this.emptyDetailTitle = emptyDetailTitle;
    }

    public ObservableCollection<TRow> Rows { get; } = [];

    public TRow? SelectedRow
    {
        get => selectedRow;
        set
        {
            if (SetField(ref selectedRow, value))
            {
                OnDetailChanged();
            }
        }
    }

    public string SelectedDetailTitle => SelectedRow?.Title ?? emptyDetailTitle;

    public string SelectedDetailStatusLine => SelectedRow?.StatusLine ?? "";

    public Brush SelectedDetailBrush => SelectedRow?.StatusBrush ?? Brushes.DimGray;

    public string SelectedDetailText => SelectedRow?.DetailText ?? "";

    public static bool IsSelectedDetailProperty(string? propertyName) =>
        string.IsNullOrEmpty(propertyName)
        || propertyName == nameof(SelectedDetailTitle)
        || propertyName == nameof(SelectedDetailStatusLine)
        || propertyName == nameof(SelectedDetailBrush)
        || propertyName == nameof(SelectedDetailText);

    public void ClearRows()
    {
        Rows.Clear();
        SelectedRow = null;
    }

    protected void ReplaceRows(IEnumerable<TRow> rows)
    {
        Rows.Clear();
        foreach (var row in rows)
        {
            Rows.Add(row);
        }
        SelectedRow = Rows.FirstOrDefault();
    }

    private void OnDetailChanged()
    {
        OnPropertyChanged(nameof(SelectedDetailTitle));
        OnPropertyChanged(nameof(SelectedDetailStatusLine));
        OnPropertyChanged(nameof(SelectedDetailBrush));
        OnPropertyChanged(nameof(SelectedDetailText));
    }
}
