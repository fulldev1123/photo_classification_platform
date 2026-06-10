from ..models import Submission
from ..schemas import SubmissionWithPhotoUrl
from ..services.photo_storage import generate_presigned_download_url


def serialize_submission(submission: Submission) -> SubmissionWithPhotoUrl:
    """Convert a ``Submission`` row into an API response, attaching a freshly
    signed, short-lived URL for its photo."""
    response = SubmissionWithPhotoUrl.model_validate(submission, from_attributes=True)
    response.photo_url = generate_presigned_download_url(submission.photo_key)
    return response
