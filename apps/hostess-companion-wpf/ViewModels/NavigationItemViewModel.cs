namespace HostessCompanion.Wpf.ViewModels;

public sealed class NavigationItemViewModel
{
    public NavigationItemViewModel(string key, string title)
    {
        Key = key;
        Title = title;
    }

    public string Key { get; }

    public string Title { get; }
}
