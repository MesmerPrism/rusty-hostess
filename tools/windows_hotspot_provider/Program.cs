using RustyHostess.WindowsHotspot;

return ProviderCli.Run(
    args,
    () => new StreamReader(Console.OpenStandardInput()),
    Console.Out,
    () => new SystemClock(),
    () => new WindowsHotspotBackend(),
    () => new FileStateStore(),
    () => new VolatileStateStore(),
    () => DateTimeOffset.UtcNow,
    ProviderAssemblyVersion.Read);
