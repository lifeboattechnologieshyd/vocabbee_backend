import structlog
from django.core.management.base import BaseCommand
from django.utils import timezone

from db.models.compete import Tournaments, TournamentParticipants

logger = structlog.get_logger("default")
from datetime import datetime

class Command(BaseCommand):
    help = "Tournament Scheduler"

    LOG_FILE = "/tmp/tournament_scheduler.log"

    def write_log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Write to file
        with open(self.LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

        # Also write to logger
        logger.info(message)

    def handle(self, *args, **kwargs):
        try:
            self.write_log("=" * 80)
            self.write_log("Tournament Scheduler Started")

            live_count = self.make_live()
            completed_count = self.make_completed()

            self.write_log(
                f"Tournament Scheduler Finished | "
                f"LIVE={live_count}, COMPLETED={completed_count}"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Scheduler completed successfully. "
                    f"LIVE={live_count}, COMPLETED={completed_count}"
                )
            )

        except Exception as e:
            self.write_log(f"Scheduler Failed: {str(e)}")
            logger.exception("Tournament Scheduler Failed")
            raise

    def make_live(self):
        self.write_log("Checking UPCOMING tournaments...")

        tournaments = Tournaments.objects.filter(
            status="UPCOMING",
            start_at__lte=timezone.now()
        )

        self.write_log(f"Found {tournaments.count()} UPCOMING tournament(s)")

        count = tournaments.update(status="LIVE")

        self.write_log(f"{count} tournament(s) moved to LIVE")

        return count

    def make_completed(self):
        self.write_log("Checking LIVE tournaments...")

        tournaments = Tournaments.objects.filter(
            status="LIVE",
            end_at__lte=timezone.now()
        )

        count = tournaments.count()

        self.write_log(f"Found {count} LIVE tournament(s) to complete")

        for tournament in tournaments:
            self.write_log(
                f"Processing Tournament ID={tournament.id}"
            )

            tournament.status = "COMPLETED"
            tournament.save(update_fields=["status"])

            self.write_log(
                f"Tournament {tournament.id} status updated to COMPLETED"
            )

            self.calculate_ranks(tournament)

            self.write_log(
                f"Tournament {tournament.id} rank calculation completed"
            )

        self.write_log(f"Completed {count} tournament(s)")

        return count

    def calculate_ranks(self, tournament):
        self.write_log(
            f"Calculating ranks for Tournament ID={tournament.id}"
        )

        participants = list(
            TournamentParticipants.objects.filter(
                tournament=tournament
            ).order_by(
                "-total_points",
                "time_taken_seconds",
                "completed_at"
            )
        )

        self.write_log(
            f"Participants found: {len(participants)}"
        )

        for rank, participant in enumerate(participants, start=1):
            participant.rank = rank

        if participants:
            TournamentParticipants.objects.bulk_update(
                participants,
                ["rank"]
            )

        self.write_log(
            f"Ranks updated for Tournament ID={tournament.id}"
        )