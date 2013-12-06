import abc
import datetime


class UnknownEngineError(Exception):
    pass


class InvalidEngineParamsError(Exception):
    pass


class ItemResponse(object):
    """Helper class for handling dictionaries that represent an item response.

    In the Engine interface below, many methods take a 'history' argument.
    Those arguments are list of dicts, often provided from UserAssessment.
    Each dict contains properties of the user's response to a single item.
    This class merely helps create and read those dictionaries and encourages
    a bit of consistency in how they are used.
    """

    # TODO(jace) provide a validation scheme

    def __init__(self, data):
        self.data = data
        if "time_done" not in self.data:
            # assume this is the creation of a new response object
            self.data["time_done"] = ItemResponse.timestamp()

    @classmethod
    def new(cls, correct, exercise, problem_type, seed, sha1, time_taken,
            attempt_content, ip_address, cards_done, skipped, opt_out,
            metadata, inconsistent_cache=False):
        data = {
            "correct": correct,
            "exercise": exercise,
            "problem_type": problem_type,
            "seed": seed,
            "sha1": sha1,
            "time_done": ItemResponse.timestamp(),
            "time_taken": time_taken,
            "attempt_content": attempt_content,
            "ip_address": ip_address,
            "cards_done": cards_done,
            "skipped": skipped,
            "opt_out": opt_out,
            "metadata": metadata,
            "inconsistent_cache": inconsistent_cache,
        }
        return cls(data)

    @property
    def time_taken(self):
        return self.data.get("time_taken")

    @property
    def correct(self):
        return self.data.get("correct")

    @property
    def exercise(self):
        return self.data.get("exercise")

    @staticmethod
    def timestamp():
        utc_datetime = datetime.datetime.utcnow()
        return utc_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")


class Engine(object):
    """Abstract base class for implementations of assessment engines.

    Engine cannot be directly instantiated. It declares the methods that must
    be implmented by a valid assessment engine.
    """

    # Abstract class; cannot be directly instantiated
    __metaclass__ = abc.ABCMeta

    # Abstract methods to be implemented in the subclasses

    @abc.abstractmethod
    def __init__(self, model_id):
        """Load the model parameters for this engine.  Should be called
        immediately after instantiaiton.

        Return type: None
        """
        pass

    @abc.abstractmethod
    def next_suggested_item(self, history):
        """Queries the engine for the next suggested item id. For now, the id
        is a string corresponding to an exercise name.

        Return type: string
        """
        pass

    @abc.abstractmethod
    def score(self, history):
        """Returns a float for the overall score on this assessment.
        Caller beware: may not be useful of valid is the assessment if the
        assessment has not been fully completed.  Check if is_complete().

        Return type: float
        """
        pass

    @abc.abstractmethod
    def readable_score(self, history):
        """Returns the score, formatted nicely as a string.

        Return type: string
        """
        pass

    # TODO(jace): add methods for subscores, and (sub)score descriptions

    @abc.abstractmethod
    def progress(self, history):
        """Returns progress of the user toward completion of the assessment.
        The progress is a float in the interval [0.0, 1.0], and is useful
        for displaying a progress bar.

        Return type: float
        """
        pass

    @abc.abstractmethod
    def estimated_exercise_accuracy(self, history, exercise_name):
        """Returns the expected probability of getting a future question
        correct on the specified exercise.  If the engine implementation
        does not support such estimation, return None.

        Return type: float or None.
        """
        pass

    @abc.abstractmethod
    def estimated_exercise_accuracies(self, history):
        """Returns a dictionary, where the keys are all the exercise names
        known by the engine to be in the domain, and the

        Returns: dict or None.
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def validate_params(raw_params):
        """Take a dictionary representing raw configuration parameters for
        an engine, validates them, peforms any type conversions that
        may be necessary, and return the cooked parameters. If the
        parameters are not valid, raises InvalidEngineParamsError.

        Returns: dict
        """
        pass

    # Inherited methods
    @staticmethod
    def lookup_engine(class_name):
        """Take a string representing the class name, which must be one of
        the implemented classes.

        Return an engine object of the appropriate
        type.
        """
        if class_name == "MIRTEngine":
            import assessment.mirt_engine
            return assessment.mirt_engine.MIRTEngine
        elif class_name == "SimpleEngine":
            import assessment.simple_engine
            return assessment.simple_engine.SimpleEngine
        elif class_name == "PretestEngine":
            import assessment.pretest_engine
            return assessment.pretest_engine.PretestEngine

        raise UnknownEngineError()

    def is_complete(self, history):
        """Take history, which is a list of dictionaries describing
        the problem attempts in the assessment thus far.
        Return a boolean representing whether the default completion criteria
        for the exercise is satisfied or if any of the problem attempts
        included a request to opt out.
        """
        opt_out = any(h['opt_out'] for h in history if 'opt_out' in h)
        return opt_out or self.progress(history) == 1.0

    def get_ab_test_condition(self):
        """Return any a/b test conditions useful for logging

        Returns a dictionary with infomation needed to log test conditions
        (For instance, if we're testing different models or question selection
        methods)
        Default return value is the json string for an empty dictionary
        """
        return {}


class ItemSuggestion(object):
    """Provides structure for the sort of object returned by the engine
    Allows for a type (i.e. exercise), an id (i.e. fractions_05), and
    a dictionary of additional data that gets recorded.

    Someday we'll use the item_type, but now it's all exercises"""
    def __init__(self, item_id, item_type="exercise", metadata={}):
        self.item_id = item_id
        self.item_type = item_type
        self.metadata = metadata
