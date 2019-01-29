import objective_turk
from objective_turk import create_hit

if __name__ == "__main__":
    objective_turk.init(objective_turk.Environment.sandbox)
    hit = create_hit.create_hit(
        Title='Test',
        Description='test',
        Question=create_hit.get_question('https://www.example.com'),
        Reward='0.50',
        AssignmentDurationInSeconds=3600,
        LifetimeInSeconds=3600 * 24 * 7,
        MaxAssignments=10,
        Keywords='survey, testing',
        QualificationRequirements=create_hit.get_qualifications(),
    )

    print(hit)
