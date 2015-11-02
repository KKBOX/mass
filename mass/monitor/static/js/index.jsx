var Info = React.createClass({
    render: function() {
        var pStyle = {
            marginBottom: 0
        };
        var reason = null;
        if ("executionResult" in this.props.job) {
            if ("reason" in this.props.job.executionResult) {
                reason = (
                    <p style={pStyle}>
                        Reason: {this.props.job.executionResult.reason}
                    </p>
                );
            }
        }

        return (
            <div>
                <p style={pStyle}>Start: {this.props.job.startTimestamp}</p>
                <p style={pStyle}>Close: {this.props.job.closeTimestamp}</p>
                <p style={pStyle}>Status: {this.props.job.closeStatus}</p>
                {reason}
            </div>
            );
    }
});

var Task = React.createClass({
    render: function() {
        var subtasks = [];
        if ("children" in this.props.task) {
            var listGroupItemStyle = {
                paddingTop: 0,
                paddingBottom: 0
            };
            var subtasks = this.props.task.children.map(function(subtask) {
                return (
                    <li style={listGroupItemStyle} className={"list-group-item"}>
                        <Task task={subtask} />
                    </li>
                    );
            });

        }
        if (!$.isEmptyObject(subtasks)) {
            subtasks = (
                <ul className={"list-group"}>
                    {subtasks}
                </ul>
            );
        }
        var pStyle = {
            marginBottom: 0
        };
        return (
            <div>
                <p style={pStyle}>{this.props.task.execution.workflowId}</p>
                {subtasks}
            </div>
            );
    }
});

var Job = React.createClass({
    handleClick: function(url) {
        if (!$.isEmptyObject(this.state.job)) {
            this.setState({
                job: {}
            });
        } else {
            var url = "/api/v1/";
            url += this.props.region + "/";
            url += this.props.domain + "/jobs/";
            url += this.props.job.execution.workflowId;
            url += "?oldest=" + this.props.oldest;

            this.getJobDetail(url)
        }
    },
    getJobDetail: function(url) {
        $.ajax({
            url: url,
            dataType: 'json',
            cache: false,
            success: function(jobs) {
                var runId = this.props.job.execution.runId;
                job = jobs.filter(function(job) {
                    return job.execution.runId == runId;
                });
                if (job.length == 1) {
                    this.setState({
                        job: job[0]
                    });
                }
            }.bind(this),
            error: function(xhr, status, err) {
                console.error(this.props.url, status, err.toString());
            }.bind(this)
        });
    },
    getInitialState: function() {
        return {
            job: {}
        };
    },
    render: function() {

        var job = null;
        if (!$.isEmptyObject(this.state.job)) {
            job = (
                <div className={"panel panel-default"}>
                    <div className={"panel-heading"}>
                        {this.props.job.execution.workflowId}
                    </div>
                    <div className={"panel-body"}>
                        <Info job={this.state.job}/>
                    </div>
                    <ul className={"list-group"}>
                        <li className={"list-group-item"}>
                            <Task task={this.state.job}/>
                        </li>
                    </ul>
                </div>
            );
        }

        var classWithStatus = "list-group-item";
        if (this.props.job.closeStatus == "COMPLETED") {
            classWithStatus += " list-group-item-success";
        } else if (this.props.job.closeStatus == "FAILED") {
            classWithStatus += " list-group-item-danger";
        } else if (this.props.job.closeStatus == "TERMINATED") {
            classWithStatus += " list-group-item-danger";
        } else if (this.props.job.closeStatus == "CANCELED") {
            classWithStatus += " list-group-item-warning";
        }

        var status = this.props.job.closeStatus;
        if (!status) {
            status = "RUNNING";
        }

        return (
            <button typeName={"button"} className={classWithStatus} onClick={this.handleClick}>
                {this.props.job.execution.workflowId}
                <span className={"badge"}>
                    {status}
                </span>
                {job}
            </button>
            );
    }
});

var JobList = React.createClass({
    getJobList: function(region, domain, oldest) {
        var url = "/api/v1/";
        url += region + "/";
        url += domain + "/jobs";
        url += "?oldest=" + oldest;
        $.ajax({
            url: url,
            dataType: 'json',
            cache: false,
            success: function(data) {
                this.setState({
                    data: data
                });
            }.bind(this),
            error: function(xhr, status, err) {
                console.error(this.props.url, status, err.toString());
            }.bind(this)
        });
    },
    getInitialState: function() {
        return {
            data: []
        };
    },
    componentWillMount: function() {
        this.getJobList(
            this.props.region,
            this.props.domain,
            this.props.oldest);
    },
    componentWillReceiveProps: function(nextProps) {
        this.getJobList(
            nextProps.region,
            nextProps.domain,
            nextProps.oldest);
    },
    render: function() {
        var region = this.props.region;
        var domain = this.props.domain;
        var oldest = this.props.oldest;
        var jobs = this.state.data.map(function(job) {
            return (
                <Job job={job} region={region} domain={domain} oldest={oldest}/>
                );
        });
        return (
            <div className={"list-group"}>
                {jobs}
            </div>
            );
    }
});

var SearchBox = React.createClass({
    getInitialState: function() {
        var now = new Date();
        var month = (now.getMonth() + 1);
        var day = now.getDate();
        if (month < 10)
            month = "0" + month;
        if (day < 10)
            day = "0" + day;
        var today = now.getFullYear() + '-' + month + '-' + day;
        return {
            region: "ap-northeast-1",
            domain: "",
            date: today
        };
    },
    handleChange: function(event) {
        this.setState({
            region: this.refs.regionInput.getDOMNode().value,
            domain: this.refs.domainInput.getDOMNode().value,
            date: this.refs.dateInput.getDOMNode().value
        });
    },
    handleClick: function() {
        var oldest = new Date(this.state.date).getTime() / 1000;
        this.props.onUserInput(
            this.state.region,
            this.state.domain,
            oldest
        );
    },
    render: function() {
        return (
            <div>
                <form>
                    <div className={"form-group"}>
                        <label>Region name</label>
                        <input type="text" placeholder="region name" value={this.state.region} ref="regionInput" className={"form-control"} onChange={this.handleChange}/>
                    </div>
                    <div className={"form-group"}>
                        <label>Domain name</label>
                        <input type="text" placeholder="domain name" value={this.state.domain} ref="domainInput" className={"form-control"} onChange={this.handleChange}/>
                    </div>
                    <div className={"form-group"}>
                        <label>Start date</label>
                        <input type="date" ref="dateInput" value={this.state.date} className={"form-control"} onChange={this.handleChange}/>
                    </div>
                </form>
                <button className={"btn btn-default"} onClick={this.handleClick}>Query</button>
            </div>);
    }
});

var Monitor = React.createClass({
    getInitialState: function() {
        // FIXME: Get initial state from searchbox.
        var now = new Date();
        var month = (now.getMonth() + 1);
        var day = now.getDate();
        if (month < 10)
            month = "0" + month;
        if (day < 10)
            day = "0" + day;
        var today = now.getFullYear() + '-' + month + '-' + day;
        var oldest = new Date(today).getTime() / 1000;
        return {
            region: "ap-northeast-1",
            domain: "",
            oldest: oldest
        };
    },
    handleUserInput: function(region, domain, oldest) {
        this.setState({
            region: region,
            domain: domain,
            oldest: oldest
        });
    },
    render: function() {
        return (
            <div className={"container-fluid"}>
                <h1>Monitor</h1>
                <SearchBox onUserInput={this.handleUserInput}/>
                <JobList region={this.state.region} domain={this.state.domain} oldest={this.state.oldest}/>
            </div>);
    }
});

React.render(
    <Monitor />,
    document.body
);
