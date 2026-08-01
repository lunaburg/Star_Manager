using System;
using System.IO;

namespace StarManager.CardMetadata.Validation
{
    internal static class Program
    {
        private static int Main()
        {
            try
            {
                NestedCardPathMatchesByNormalizedFileName();
                RepeatedFileStreamKeepsFirstSnapshot();
                OverwriteConsumesDiskSnapshot();
                MismatchStillClearsSnapshot();
                Console.WriteLine("Card metadata save-target validation passed (4 scenarios). ");
                return 0;
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine(exception.Message);
                return 1;
            }
        }

        private static void NestedCardPathMatchesByNormalizedFileName()
        {
            var pending = new PendingSaveTarget<string>();
            string target = CardPath("female", "cloth", "古装", "a", "sr (25).png");
            Capture(pending, target, "nested-disk-metadata");

            SaveTargetConsumption<string> consumed = pending.Consume(
                "cloth/古装/a/sr (25).png"
            );

            Assert(consumed.Matches, "Nested card path did not match its disk target.");
            Assert(
                consumed.Value == "nested-disk-metadata",
                "Nested card metadata was not preserved."
            );
            Assert(!pending.IsKnown, "Nested card snapshot was not consumed.");
        }

        private static void RepeatedFileStreamKeepsFirstSnapshot()
        {
            var pending = new PendingSaveTarget<string>();
            string target = CardPath("female", "repeat.png");
            int captureCount = 0;
            Capture(pending, target, "first", () => captureCount++);

            bool repeatedCaptured = pending.TryCapture(
                target.ToUpperInvariant(),
                () =>
                {
                    captureCount++;
                    return "second";
                },
                out _,
                out _
            );
            SaveTargetConsumption<string> consumed = pending.Consume("repeat.png");

            Assert(!repeatedCaptured, "Repeated FileStream capture was accepted.");
            Assert(captureCount == 1, "Repeated FileStream reread the disk target.");
            Assert(consumed.Value == "first", "Repeated capture replaced the first snapshot.");
        }

        private static void OverwriteConsumesDiskSnapshot()
        {
            var pending = new PendingSaveTarget<string>();
            string target = CardPath("female", "folders", "overwrite.png");
            Capture(pending, target, "existing-card-metadata");

            SaveTargetConsumption<string> consumed = pending.Consume("overwrite.png");

            Assert(consumed.WasKnown, "Overwrite target was not recorded.");
            Assert(consumed.Matches, "Overwrite target did not match the saved card.");
            Assert(
                consumed.Value == "existing-card-metadata",
                "Overwrite did not return the disk snapshot."
            );
            Assert(!pending.IsKnown, "Overwrite snapshot remained after save consumption.");
        }

        private static void MismatchStillClearsSnapshot()
        {
            var pending = new PendingSaveTarget<string>();
            Capture(pending, CardPath("female", "expected.png"), "stale");

            SaveTargetConsumption<string> consumed = pending.Consume("different.png");

            Assert(!consumed.Matches, "Mismatched target was incorrectly accepted.");
            Assert(consumed.Value == null, "Mismatched target leaked disk metadata.");
            Assert(!pending.IsKnown, "Mismatched save left a stale snapshot behind.");

            Capture(pending, CardPath("female", "expected.png"), "fresh");
            Assert(
                pending.Consume("expected.png").Value == "fresh",
                "A save after mismatch could not capture a fresh snapshot."
            );
        }

        private static string CardPath(params string[] parts)
        {
            string path = Path.Combine(Path.GetTempPath(), "StarManagerCardMetadataValidation");
            foreach (string part in parts)
            {
                path = Path.Combine(path, part);
            }
            return path;
        }

        private static void Capture(
            PendingSaveTarget<string> pending,
            string path,
            string value,
            Action onCapture = null
        )
        {
            bool captured = pending.TryCapture(
                path,
                () =>
                {
                    onCapture?.Invoke();
                    return value;
                },
                out _,
                out _
            );
            Assert(captured, $"Could not capture save target: {path}");
        }

        private static void Assert(bool condition, string message)
        {
            if (!condition)
            {
                throw new InvalidOperationException(message);
            }
        }
    }
}
