import objective_turk

QUESTION = """<?xml version="1.0"?>
<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
<HTMLContent><![CDATA[
    <!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    <div class="container">
      <p> test test test test test </p>
      <p>
        At the end of the study, you will receive a completion code. Please
        enter it here to receive your payment for participating in this study:
      </p>
      <form id="mturk_form" target="" method="POST">
        <input type="hidden" value="" name="assignmentId" id="assignmentId" />
        <p>
          <input
            name="completion_code"
            type="text"
            placeholder="Enter your completion code here"
          />
          <input type="submit" id='submitButton' />
        </p>
      </form>
    </div>
    <script type='text/javascript' src='https://s3.amazonaws.com/mturk-public/externalHIT_v1.js'></script>
    <script language='Javascript'>turkSetAssignmentID();</script>
  </body>
</html>

]]></HTMLContent>
<FrameHeight>10</FrameHeight>
</HTMLQuestion>
"""

if __name__ == "__main__":
    objective_turk.init(objective_turk.Environment.sandbox)
    hit = objective_turk.create_hit.create_hit(
        Title='Test',
        Description='test',
        Reward='0.50',
        AssignmentDurationInSeconds=3600,
        LifetimeInSeconds=3600 * 24 * 7,
        MaxAssignments=10,
        Keywords='survey, testing',
        QualificationRequirements=objective_turk.create_hit.get_qualifications(),
        Question=QUESTION
    )

    print(hit)
