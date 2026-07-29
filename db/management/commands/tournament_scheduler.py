import structlog
from django.core.management.base import BaseCommand
from django.utils import timezone

from db.models.compete import Tournaments, TournamentParticipants

logger = structlog.get_logger("default")
from datetime import datetime


class Command(BaseCommand):

    help = "Tournament Scheduler"

    def handle(self, *args, **kwargs):
        with open("/tmp/tournament_scheduler.log", "a") as f:
            f.write(f"Executed at {datetime.now()}\n")
        logger.info("Tournament Scheduler CRON JOB")
        logger.info("UPCOMING to LIVE ====")
        self.make_live()
        logger.info("LIVE to COMPLETED")
        self.make_completed()
        self.stdout.write(
            self.style.SUCCESS("Tournament scheduler executed successfully.")
        )

    def make_live(self):
        tournaments = Tournaments.objects.filter(
            status="UPCOMING",
            start_at__lte=timezone.now()
        )
        count = tournaments.update(
            status="LIVE"
        )
        logger.info(count)
        logger.info("UPCOMING to LIVE Completed")
        self.stdout.write(
            self.style.SUCCESS(f"{count} tournament(s) moved to LIVE.")
        )

    def make_completed(self):
        tournaments = Tournaments.objects.filter(
            status="LIVE",
            end_at__lte=timezone.now()
        )
        logger.info("LIVE TOURNAMENTS TO MOVE TO COMPLETED ARE ====")
        logger.info(len(tournaments))

        for tournament in tournaments:
            tournament.status = "COMPLETED"
            tournament.save(update_fields=["status"])
            logger.info("One tournament moved to completed but about to calculate rankings")
            self.calculate_ranks(tournament)

        self.stdout.write(
            self.style.SUCCESS(f"{tournaments.count()} tournament(s) completed.")
        )

    def calculate_ranks(self, tournament):
        participants = list(
            TournamentParticipants.objects.filter(
                tournament=tournament
            ).order_by(
                "-total_points",
                "time_taken_seconds",
                "completed_at"
            )
        )
        rank = 1
        for participant in participants:
            participant.rank = rank
            rank += 1
        TournamentParticipants.objects.bulk_update(
            participants,
            ["rank"]
        )
        logger.info("One tournament rank calculations are completed")