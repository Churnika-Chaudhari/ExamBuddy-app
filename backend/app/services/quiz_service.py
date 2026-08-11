import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.enums import QuizDifficulty, QuizType
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.generated_notes_repository import GeneratedNotesRepository
from app.repositories.notes_repository import NotesRepository
from app.repositories.quiz_repository import (
    QuizAnalysisRepository,
    QuizAttemptRepository,
    QuizRepository,
)
from app.repositories.stats_repository import StatsRepository
from app.services.ai.ai_service import AIService
from app.services.mappers import map_document_response, map_quiz_response
from app.utils.topic_extractor import filter_topics
from app.utils.subject_detector import resolve_document_subject

logger = logging.getLogger(__name__)


def _normalize_subject(name: str) -> str:
    return " ".join(name.strip().split())


def _topics_from_analysis_doc(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    topics: list[dict[str, Any]] = []

    def add(topic: str, *, unit: str | None = None, frequency: int = 1, importance: str | None = None):
        t = topic.strip()
        if not t or t.lower() in seen:
            return
        if not filter_topics([t]):
            return
        seen.add(t.lower())
        topics.append(
            {
                "topic": t,
                "unit": unit,
                "frequency": frequency,
                "importance": importance,
            }
        )

    for row in analysis.get("topic_frequency_table") or []:
        if isinstance(row, dict):
            add(
                row.get("topic", ""),
                unit=row.get("unit"),
                frequency=int(row.get("frequency") or 1),
                importance=row.get("importance"),
            )

    for bucket, importance in (
        ("high_priority_topics", "High"),
        ("medium_priority_topics", "Medium"),
        ("low_priority_topics", "Low"),
        ("most_important_topics", "High"),
        ("frequently_asked_topics", "Medium"),
        ("rarely_asked_topics", "Low"),
    ):
        for row in analysis.get(bucket) or []:
            if isinstance(row, dict):
                add(
                    row.get("topic", ""),
                    unit=row.get("unit"),
                    frequency=int(row.get("frequency") or 1),
                    importance=importance,
                )

    for row in analysis.get("important_topics") or []:
        if isinstance(row, dict):
            add(row.get("topic", ""), frequency=1)

    freq = analysis.get("topic_frequency") or {}
    if isinstance(freq, dict):
        for topic, count in sorted(freq.items(), key=lambda x: x[1], reverse=True):
            add(str(topic), frequency=int(count or 1))

    for topic in analysis.get("syllabus_topics") or []:
        if isinstance(topic, str):
            add(topic)

    topics.sort(key=lambda x: x.get("frequency", 0), reverse=True)
    return topics


class QuizService:
    def __init__(
        self,
        quiz_repo: QuizRepository,
        attempt_repo: QuizAttemptRepository,
        analysis_repo: AnalysisRepository,
        document_repo: DocumentRepository,
        generated_notes_repo: GeneratedNotesRepository,
        notes_repo: NotesRepository,
        stats_repo: StatsRepository,
        analysis_stats_repo: QuizAnalysisRepository,
        ai_service: AIService | None = None,
    ) -> None:
        self.quiz_repo = quiz_repo
        self.attempt_repo = attempt_repo
        self.analysis_repo = analysis_repo
        self.document_repo = document_repo
        self.generated_notes_repo = generated_notes_repo
        self.notes_repo = notes_repo
        self.stats_repo = stats_repo
        self.analysis_stats_repo = analysis_stats_repo
        self.ai_service = ai_service or AIService()

    async def get_available_subjects(self, user_id: str) -> list[dict[str, Any]]:
        subject_map: dict[str, dict[str, Any]] = {}

        def bump(name: str, *, analyses=0, topics=0, documents=0):
            key = _normalize_subject(name)
            if not key:
                return
            if key not in subject_map:
                subject_map[key] = {
                    "name": key,
                    "analysis_count": 0,
                    "topic_count": 0,
                    "document_count": 0,
                }
            subject_map[key]["analysis_count"] += analyses
            subject_map[key]["topic_count"] += topics
            subject_map[key]["document_count"] += documents

        analyses = await self.analysis_repo.list_by_user(user_id, limit=100)
        for analysis in analyses:
            if analysis.get("status") != "completed":
                continue
            subject = analysis.get("subject")
            if not subject:
                continue
            topic_rows = _topics_from_analysis_doc(analysis)
            bump(subject, analyses=1, topics=len(topic_rows))

        docs = await self.document_repo.list_by_user(user_id, skip=0, limit=200)
        for doc in docs:
            subject = doc.get("subject")
            if subject:
                bump(subject, documents=1)

        return sorted(subject_map.values(), key=lambda s: s["name"].lower())

    async def get_subject_topics(self, user_id: str, subject: str) -> dict[str, Any]:
        subject = _normalize_subject(subject)
        if not subject:
            raise ValidationAppError("Subject is required")

        analyses = await self.analysis_repo.list_by_user(user_id, limit=100)
        topic_map: dict[str, dict[str, Any]] = {}
        analysis_ids: list[str] = []

        for analysis in analyses:
            if analysis.get("status") != "completed":
                continue
            analysis_subject = _normalize_subject(analysis.get("subject") or "")
            if analysis_subject.lower() != subject.lower():
                continue
            analysis_ids.append(str(analysis["_id"]))
            for row in _topics_from_analysis_doc(analysis):
                key = row["topic"].lower()
                if key not in topic_map or row["frequency"] > topic_map[key]["frequency"]:
                    topic_map[key] = row

        topics = sorted(topic_map.values(), key=lambda x: x.get("frequency", 0), reverse=True)
        if not topics:
            raise NotFoundError(f"No topics found for subject: {subject}")

        return {
            "subject": subject,
            "topics": topics,
            "analysis_ids": analysis_ids,
        }

    async def _build_subject_context(
        self,
        user_id: str,
        subject: str,
        topics: list[str],
        analysis_id: str | None,
    ) -> tuple[str, list[str], str | None]:
        content_parts: list[str] = []
        resolved_analysis_id = analysis_id
        subject = _normalize_subject(subject)

        analyses = await self.analysis_repo.list_by_user(user_id, limit=100)
        matched = []
        for analysis in analyses:
            if analysis.get("status") != "completed":
                continue
            a_subject = _normalize_subject(analysis.get("subject") or "")
            if subject and a_subject.lower() == subject.lower():
                matched.append(analysis)
            elif analysis_id and str(analysis["_id"]) == analysis_id:
                matched.append(analysis)

        if analysis_id and not any(str(a["_id"]) == analysis_id for a in matched):
            single = await self.analysis_repo.get_by_id_and_user(analysis_id, user_id)
            if single and single.get("status") == "completed":
                matched.append(single)

        if not matched and subject:
            raise NotFoundError(f"No completed analysis found for subject: {subject}")

        all_topic_names: list[str] = list(topics)
        for analysis in matched:
            if not resolved_analysis_id:
                resolved_analysis_id = str(analysis["_id"])
            if analysis.get("summary"):
                content_parts.append(f"Analysis summary:\n{analysis['summary'][:3000]}")
            for row in _topics_from_analysis_doc(analysis):
                t = row["topic"]
                if not all_topic_names or t in all_topic_names:
                    all_topic_names.append(t)

        all_topic_names = filter_topics(list(dict.fromkeys(all_topic_names)))[:25]

        docs = await self.document_repo.list_by_user(user_id, skip=0, limit=300)
        for doc in docs:
            doc_subject = _normalize_subject(
                resolve_document_subject(
                    explicit_subject=doc.get("subject"),
                    filename=doc.get("title"),
                    title=doc.get("title"),
                )
                or ""
            )
            if doc_subject.lower() != subject.lower():
                continue
            extracted = (doc.get("extracted_text") or "").strip()
            if extracted:
                label = doc.get("title") or "Reference material"
                content_parts.append(f"{label}:\n{extracted[:6000]}")

        gen_notes = await self.generated_notes_repo.list_by_user(user_id, limit=100)
        for note in gen_notes:
            note_subject = _normalize_subject(note.get("subject") or "")
            if subject and note_subject and note_subject.lower() != subject.lower():
                continue
            topic_name = note.get("topic", "")
            if all_topic_names and topic_name not in all_topic_names:
                continue
            notes_text = (note.get("notes") or "")[:4000]
            if notes_text:
                content_parts.append(f"Study notes — {topic_name}:\n{notes_text}")

        content = "\n\n".join(content_parts)
        return content, all_topic_names, resolved_analysis_id

    async def generate_quiz(
        self,
        user_id: str,
        *,
        notes_id: str | None,
        analysis_id: str | None,
        subject: str | None,
        topics: list[str],
        title: str | None,
        quiz_type: QuizType,
        difficulty: QuizDifficulty,
        num_questions: int,
        time_limit_minutes: int | None,
    ) -> dict[str, Any]:
        content = ""
        source_notes_id = None
        source_analysis_id = analysis_id
        resolved_subject = _normalize_subject(subject) if subject else None
        resolved_topics = filter_topics(topics) if topics else []

        if subject:
            content, resolved_topics, source_analysis_id = await self._build_subject_context(
                user_id, subject, resolved_topics, analysis_id
            )
            title = title or f"{resolved_subject} Quiz"
        elif notes_id:
            note = await self.notes_repo.get_by_id_and_user(notes_id, user_id)
            if not note:
                raise NotFoundError("Note not found")
            content = note.get("content", "")
            resolved_topics = resolved_topics or filter_topics(note.get("topics", []))
            source_notes_id = notes_id
            title = title or f"Quiz - {note.get('title', 'Notes')}"

        if not content and not resolved_topics:
            raise ValidationAppError(
                "Select a subject with analyzed topics, or provide notes_id / topics"
            )

        if not resolved_subject:
            raise ValidationAppError("Subject is required for quiz generation")

        logger.info(
            "Generating quiz subject=%s topics=%d type=%s difficulty=%s",
            resolved_subject,
            len(resolved_topics),
            quiz_type.value,
            difficulty.value,
        )

        result, metadata = await self.ai_service.generate_quiz(
            content=content,
            topics=resolved_topics,
            quiz_type=quiz_type.value,
            num_questions=num_questions,
            difficulty=difficulty.value,
            subject=resolved_subject,
        )

        questions = result.get("questions", [])
        for question in questions:
            if not question.get("id"):
                question["id"] = str(uuid.uuid4())

        now = datetime.now(UTC)
        quiz = await self.quiz_repo.create(
            {
                "user_id": self.quiz_repo.to_object_id(user_id),
                "title": title or result.get("title", "Generated Quiz"),
                "subject": resolved_subject,
                "difficulty": difficulty,
                "source_notes_id": (
                    self.quiz_repo.to_object_id(source_notes_id) if source_notes_id else None
                ),
                "source_analysis_id": (
                    self.quiz_repo.to_object_id(source_analysis_id)
                    if source_analysis_id
                    else None
                ),
                "source_topics": resolved_topics,
                "quiz_type": quiz_type,
                "questions": questions,
                "total_questions": len(questions),
                "time_limit_minutes": time_limit_minutes,
                "ai_metadata": metadata,
                "created_at": now,
            }
        )

        await self.stats_repo.add_activity(
            user_id,
            {
                "type": "quiz_generated",
                "ref_id": str(quiz["_id"]),
                "title": quiz["title"],
                "timestamp": now,
            },
        )
        return map_quiz_response(quiz)

    async def list_quizzes(
        self,
        user_id: str,
        *,
        page: int,
        limit: int,
        subject: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * limit
        query: dict[str, Any] = {"user_id": self.quiz_repo.to_object_id(user_id)}
        if subject:
            query["subject"] = subject
        quizzes = await self.quiz_repo.list_by_user(user_id, skip=skip, limit=limit, subject=subject)
        total = await self.quiz_repo.count(query)
        return [map_quiz_response(quiz) for quiz in quizzes], total

    async def get_quiz(self, quiz_id: str, user_id: str) -> dict[str, Any]:
        quiz = await self.quiz_repo.get_by_id_and_user(quiz_id, user_id)
        if not quiz:
            raise NotFoundError("Quiz not found")
        return map_quiz_response(quiz)

    def _grade_answer(self, user_answer: str, correct_answer: str, question_type: str) -> bool:
        user = user_answer.strip().lower()
        correct = correct_answer.strip().lower()
        if not user:
            return False
        if question_type in (QuizType.MCQ, QuizType.TRUE_FALSE, QuizType.FILL_BLANK):
            return user == correct
        if user in correct or correct in user:
            return True
        user_words = set(user.split())
        correct_words = set(correct.split())
        if len(correct_words) <= 3:
            return user == correct
        overlap = len(user_words & correct_words) / max(len(correct_words), 1)
        return overlap >= 0.6

    async def submit_quiz(
        self,
        quiz_id: str,
        user_id: str,
        answers: list[dict[str, str]],
        time_taken_seconds: int | None,
    ) -> dict[str, Any]:
        quiz = await self.quiz_repo.get_by_id_and_user(quiz_id, user_id)
        if not quiz:
            raise NotFoundError("Quiz not found")

        question_map = {q["id"]: q for q in quiz.get("questions", [])}
        graded_answers: list[dict[str, Any]] = []
        correct_count = 0
        topic_stats: dict[str, dict[str, int]] = {}

        for answer in answers:
            question = question_map.get(answer["question_id"])
            if not question:
                continue
            user_answer = answer["user_answer"].strip()
            correct_answer = str(question.get("correct_answer", "")).strip()
            q_type = str(question.get("question_type", QuizType.MCQ))
            is_correct = self._grade_answer(user_answer, correct_answer, q_type)
            if is_correct:
                correct_count += 1

            topic = question.get("topic") or "General"
            if topic not in topic_stats:
                topic_stats[topic] = {"correct": 0, "total": 0}
            topic_stats[topic]["total"] += 1
            if is_correct:
                topic_stats[topic]["correct"] += 1

            graded_answers.append(
                {
                    "question_id": answer["question_id"],
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "explanation": question.get("explanation"),
                    "topic": question.get("topic"),
                }
            )

        total_count = len(quiz.get("questions", []))
        score = round((correct_count / total_count) * 100, 2) if total_count else 0.0
        completed_at = datetime.now(UTC)
        subject = quiz.get("subject")

        attempt = await self.attempt_repo.create(
            {
                "user_id": self.attempt_repo.to_object_id(user_id),
                "quiz_id": self.attempt_repo.to_object_id(quiz_id),
                "quiz_title": quiz.get("title"),
                "subject": subject,
                "difficulty": quiz.get("difficulty"),
                "quiz_type": quiz.get("quiz_type"),
                "answers": graded_answers,
                "score": score,
                "correct_count": correct_count,
                "total_count": total_count,
                "time_taken_seconds": time_taken_seconds,
                "completed_at": completed_at,
            }
        )

        for topic, stats in topic_stats.items():
            await self.analysis_stats_repo.upsert_topic_stats(
                user_id,
                subject,
                topic,
                correct=stats["correct"],
                total=stats["total"],
            )

        await self.stats_repo.increment_field(user_id, "quizzes_taken")
        await self.stats_repo.add_activity(
            user_id,
            {
                "type": "quiz_completed",
                "ref_id": str(attempt["_id"]),
                "title": f"Scored {score}% on {quiz.get('title', 'Quiz')}",
                "timestamp": completed_at,
            },
        )

        return {
            "attempt_id": str(attempt["_id"]),
            "quiz_id": quiz_id,
            "subject": subject,
            "difficulty": quiz.get("difficulty"),
            "quiz_title": quiz.get("title"),
            "score": score,
            "correct_count": correct_count,
            "total_count": total_count,
            "answers": graded_answers,
            "completed_at": completed_at,
        }

    async def list_attempt_history(
        self,
        user_id: str,
        *,
        page: int,
        limit: int,
        subject: str | None = None,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * limit
        attempts = await self.attempt_repo.list_by_user(
            user_id, skip=skip, limit=limit, subject=subject, search=search
        )
        total = await self.attempt_repo.count_by_user(user_id, subject=subject)
        return [map_document_response(a) for a in attempts], total

    async def get_attempt(self, attempt_id: str, user_id: str) -> dict[str, Any]:
        attempt = await self.attempt_repo.get_by_id_and_user(attempt_id, user_id)
        if not attempt:
            raise NotFoundError("Quiz attempt not found")
        return map_document_response(attempt)

    async def delete_attempt(self, attempt_id: str, user_id: str) -> None:
        deleted = await self.attempt_repo.delete(attempt_id, user_id)
        if not deleted:
            raise NotFoundError("Quiz attempt not found")

    async def get_quiz_attempts(self, quiz_id: str, user_id: str) -> list[dict[str, Any]]:
        quiz = await self.quiz_repo.get_by_id_and_user(quiz_id, user_id)
        if not quiz:
            raise NotFoundError("Quiz not found")
        attempts = await self.attempt_repo.list_by_quiz(quiz_id, user_id)
        return [map_document_response(attempt) for attempt in attempts]

    async def get_quiz_analysis(self, user_id: str, *, subject: str | None = None) -> dict[str, Any]:
        stats = await self.attempt_repo.score_stats(user_id, subject=subject)
        weak = await self.analysis_stats_repo.list_by_user(
            user_id, subject=subject, sort_asc=True, limit=8
        )
        strong = await self.analysis_stats_repo.list_by_user(
            user_id, subject=subject, sort_asc=False, limit=8
        )
        weekly = await self.attempt_repo.weekly_progress(user_id, subject=subject)
        trend = await self.attempt_repo.score_trend(user_id, subject=subject, limit=20)
        distribution = await self.analysis_stats_repo.list_by_user(
            user_id, subject=subject, limit=30
        )

        suggestions: list[str] = []
        for row in weak[:5]:
            topic = row.get("topic", "")
            acc = row.get("accuracy_percentage", 0)
            if topic and acc < 70:
                suggestions.append(f"Revise {topic}.")
                suggestions.append(f"Practice {topic} questions from your PYQs.")

        if not suggestions and stats["count"] == 0:
            label = subject or "this subject"
            suggestions.append(f"Take your first {label} quiz to unlock personalized suggestions.")

        return {
            "subject": subject,
            "total_quizzes_attempted": stats["count"],
            "average_score": stats["avg_score"],
            "highest_score": stats["max_score"],
            "lowest_score": stats["min_score"],
            "total_questions_solved": stats["total_questions"],
            "weak_topics": [
                {
                    "topic": row.get("topic", ""),
                    "subject": row.get("subject"),
                    "accuracy_percentage": row.get("accuracy_percentage", 0),
                    "attempts": row.get("attempts", 0),
                    "correct": row.get("correct", 0),
                    "total": row.get("total", 0),
                }
                for row in weak
            ],
            "strong_topics": [
                {
                    "topic": row.get("topic", ""),
                    "subject": row.get("subject"),
                    "accuracy_percentage": row.get("accuracy_percentage", 0),
                    "attempts": row.get("attempts", 0),
                    "correct": row.get("correct", 0),
                    "total": row.get("total", 0),
                }
                for row in strong
            ],
            "improvement_suggestions": suggestions[:6],
            "weekly_progress": weekly,
            "score_trend": trend,
            "topic_strength_distribution": [
                {
                    "topic": row.get("topic", ""),
                    "subject": row.get("subject"),
                    "accuracy_percentage": row.get("accuracy_percentage", 0),
                    "attempts": row.get("attempts", 0),
                    "correct": row.get("correct", 0),
                    "total": row.get("total", 0),
                }
                for row in distribution
            ],
        }

    async def delete_quiz(self, quiz_id: str, user_id: str) -> None:
        deleted = await self.quiz_repo.delete(quiz_id, user_id)
        if not deleted:
            raise NotFoundError("Quiz not found")
        await self.attempt_repo.delete_by_quiz(quiz_id, user_id)

    async def clear_quizzes(self, user_id: str) -> int:
        # Removes the generated quiz list shown on the generator screen.
        # Attempt history and analytics are intentionally preserved.
        return await self.quiz_repo.delete_all_by_user(user_id)
