$(document).ready(function() {
    $('#members-filter-form').submit(function(event) {
        event.preventDefault();
        fetch_members();
    });

    // Submit the form on page load
    fetch_members();

    // Re-submit the form when checkboxes change
    $('#members-filter-form input[type="checkbox"]').change(function() {
        $('#members-filter-form').submit();
    });
});

$(document).ready(function() {
    $('#members-filter-form').submit(function(event) {
        event.preventDefault();
        fetch_members();
    });
});

async function fetch_members() {
    const form_data = $('#members-filter-form').serialize();
    try {
        const response = await $.ajax({
            url: "/admin/get_members",
            data: form_data,
            dataType: 'json'
        });
        const members = response.members
        render_table(members);
        // render_edit_forms(members)
    } catch (error) {
        console.error("AJAX error:", error);
    }
}

function render_table(members) {
    const members_container = $('#members-table');
    if (members.length === 0) {
        members_container.html('<h2>No Members Please Add</h2>');
        return;
    }

    let members_html = `
        <div class="ampire-table">
            <h2>Mga Tao</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th scope="col">ID Number</th>
                        <th scope="col">Name</th>
                        <th scope="col">Position</th>
                        <th scope="col">Section</th>
                    </tr>
                </thead>
                <tbody>`;

    members.forEach(members => {
        members_html += `
            <tr>
                <th scope="row">${members.id}</th>
                <td>${members.name}</td>
                <td>${members.position}</td>
                <td>${members.section}</td>
            </tr>`;
    });
    
    members_html += `
                </tbody>
            </table>
        </div>`;

    members_container.html(members_html);
}

function render_edit_forms(members) {
    const edit_form_container = $('#edit-form-container');
    if (members.length === 0) {
        members_container.html('<h2>No Members Please Add</h2>');
        return;
    }

    let edit_form_html = ``;

    members.forEach(members => {
        edit_form_html += `
            <div class="modal fade" id="editModal-${members.pk}" tabindex="-1" role="dialog" aria-labelledby="editModal-${members.pk}Label" aria-hidden="true">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="editModal-${members.pk}Label">Edit Form</h5>
                            <button type="button" class="btn-close" data-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form action="{% url 'admin:edit_member' ${members.pk} %}" method="post">
                                ${csrfToken}
                                ${edit_member_form}
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                                    <button type="submit" class="btn btn-success">Submit</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    edit_form_container.html(edit_form_html);
}