from rest_framework import serializers

from .models import ExamSession


class ExamStartSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=[20, 50])


class ExamAnswerSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    answer = serializers.IntegerField(allow_null=True, required=False)


class ExamSessionItemSerializer(serializers.Serializer):
    question = serializers.IntegerField(source="question_id")
    answer = serializers.IntegerField(source="answer_id", allow_null=True)
    is_correct = serializers.BooleanField(allow_null=True)


class ExamSessionSerializer(serializers.ModelSerializer):
    total = serializers.IntegerField(read_only=True)
    passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = ExamSession
        fields = ("id", "mode", "started_at", "ends_at", "finished_at",
                  "score", "total", "pass_score", "passed")


class ExamResultSerializer(ExamSessionSerializer):
    items = ExamSessionItemSerializer(many=True, read_only=True)

    class Meta(ExamSessionSerializer.Meta):
        fields = ExamSessionSerializer.Meta.fields + ("items",)
