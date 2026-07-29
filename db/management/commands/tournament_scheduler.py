import structlog
from django.core.management.base import BaseCommand
from django.utils import timezone

from db.models.compete import Tournaments, TournamentParticipants

logger = structlog.get_logger("default")
from datetime import datetime

class Command(BaseCommand):
    help = "Tournament Scheduler"

    def handle(self, *args, **kwargs):
        try:
            # Temporary debug (remove after verification)
            with open("/tmp/tournament_scheduler.log", "a") as f:
                f.write(f"Executed at {datetime.now()}\n")

            logger.info("========== Tournament Scheduler Started ==========")

            live_count = self.make_live()
            completed_count = self.make_completed()

            logger.info(
                f"Tournament Scheduler Completed | "
                f"Moved to LIVE: {live_count}, "
                f"Moved to COMPLETED: {completed_count}"
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Scheduler completed successfully. "
                    f"LIVE: {live_count}, COMPLETED: {completed_count}"
                )
            )

        except Exception:
            logger.exception("Tournament Scheduler Failed")
            raise

    def make_live(self):
        logger.info("Checking UPCOMING tournaments...")

        tournaments = Tournaments.objects.filter(
            status="UPCOMING",
            start_at__lte=timezone.now()
        )

        count = tournaments.update(status="LIVE")

        logger.info(f"{count} tournament(s) moved to LIVE.")

        return count

    def make_completed(self):
        logger.info("Checking LIVE tournaments...")

        tournaments = Tournaments.objects.filter(
            status="LIVE",
            end_at__lte=timezone.now()
        )

        count = tournaments.count()

        logger.info(f"Found {count} tournament(s) to complete.")

        for tournament in tournaments:
            logger.info(
                f"Processing Tournament ID={tournament.id}"
            )

            tournament.status = "COMPLETED"
            tournament.save(update_fields=["status"])

            self.calculate_ranks(tournament)

            logger.info(
                f"Tournament ID={tournament.id} marked COMPLETED."
            )

        return count

    def calculate_ranks(self, tournament):
        logger.info(
            f"Calculating ranks for Tournament ID={tournament.id}"
        )

        participants = list(
            TournamentParticipants.objects.filter(
                tournament=tournament
            ).order_by(
                "-total_points",
                "time_taken_seconds",
                "completed_at",
            )
        )

        logger.info(
            f"Participants found: {len(participants)}"
        )

        for rank, participant in enumerate(participants, start=1):
            participant.rank = rank

        if participants:
            TournamentParticipants.objects.bulk_update(
                participants,
                ["rank"],
            )

        logger.info(
            f"Rank calculation completed for Tournament ID={tournament.id}"
        )