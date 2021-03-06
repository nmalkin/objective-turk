import objective_turk
import objective_turk.create_hit

if __name__ == "__main__":
    objective_turk.init(objective_turk.Environment.sandbox)
    hit = objective_turk.create_hit.create_hit(
        Title='Test',
        Description='test',
        Question=objective_turk.create_hit.get_external_question('https://www.example.com'),
        Reward='0.50',
        AssignmentDurationInSeconds=3600,
        LifetimeInSeconds=3600 * 24 * 7,
        MaxAssignments=10,
        Keywords='survey, testing',
        QualificationRequirements=objective_turk.create_hit.get_qualifications(),
    )

    print(hit)
