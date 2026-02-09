import { useState, useEffect } from 'react';
import type { ReactElement } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { studyApi } from '../api/client';
import type { StudyGuide } from '../api/client';
import { CourseAssignSelect } from '../components/CourseAssignSelect';
import './StudyGuidePage.css';

function renderInline(text: string) {
  // Minimal inline markdown support for bold text.
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    return <span key={idx}>{part}</span>;
  });
}

function renderGuideContent(content: string) {
  const lines = content.split('\n');
  const blocks: ReactElement[] = [];
  let i = 0;

  while (i < lines.length) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      i++;
      continue;
    }

    if (line.startsWith('# ')) {
      blocks.push(<h1 key={`h1-${i}`}>{line.substring(2)}</h1>);
      i++;
      continue;
    }

    if (line.startsWith('## ')) {
      blocks.push(<h2 key={`h2-${i}`}>{line.substring(3)}</h2>);
      i++;
      continue;
    }

    if (line.startsWith('### ')) {
      blocks.push(<h3 key={`h3-${i}`}>{line.substring(4)}</h3>);
      i++;
      continue;
    }

    const isUnordered = line.startsWith('- ') || line.startsWith('* ');
    const isOrdered = /^\d+\.\s/.test(line);

    if (isUnordered || isOrdered) {
      const listItems: ReactElement[] = [];
      const ordered = isOrdered;

      while (i < lines.length) {
        const candidate = lines[i].trim();
        if (!candidate) break;

        if (ordered && /^\d+\.\s/.test(candidate)) {
          listItems.push(
            <li key={`li-${i}`}>{renderInline(candidate.replace(/^\d+\.\s/, ''))}</li>
          );
          i++;
          continue;
        }

        if (!ordered && (candidate.startsWith('- ') || candidate.startsWith('* '))) {
          listItems.push(<li key={`li-${i}`}>{renderInline(candidate.substring(2))}</li>);
          i++;
          continue;
        }

        break;
      }

      blocks.push(
        ordered ? <ol key={`ol-${i}`}>{listItems}</ol> : <ul key={`ul-${i}`}>{listItems}</ul>
      );
      continue;
    }

    const paragraphLines: string[] = [];
    while (i < lines.length) {
      const candidate = lines[i].trim();
      if (!candidate) break;
      if (
        candidate.startsWith('# ') ||
        candidate.startsWith('## ') ||
        candidate.startsWith('### ') ||
        candidate.startsWith('- ') ||
        candidate.startsWith('* ') ||
        /^\d+\.\s/.test(candidate)
      ) {
        break;
      }
      paragraphLines.push(candidate);
      i++;
    }

    blocks.push(
      <p key={`p-${i}`}>
        {renderInline(paragraphLines.join(' '))}
      </p>
    );
  }

  return blocks;
}

export function StudyGuidePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [guide, setGuide] = useState<StudyGuide | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGuide = async () => {
      if (!id) return;
      try {
        const data = await studyApi.getGuide(parseInt(id));
        setGuide(data);
      } catch (err) {
        setError('Failed to load study guide');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchGuide();
  }, [id]);

  const handleDelete = async () => {
    if (!guide || !confirm('Are you sure you want to delete this study guide?')) return;
    try {
      await studyApi.deleteGuide(guide.id);
      navigate('/dashboard');
    } catch (err) {
      setError('Failed to delete study guide');
    }
  };

  if (loading) {
    return (
      <div className="study-guide-page">
        <div className="loading">Loading study guide...</div>
      </div>
    );
  }

  if (error || !guide) {
    return (
      <div className="study-guide-page">
        <div className="error">{error || 'Study guide not found'}</div>
        <Link to="/dashboard" className="back-link">Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="study-guide-page">
      <div className="study-guide-header">
        <Link to="/dashboard" className="back-link">&larr; Back to Dashboard</Link>
        <div className="header-actions">
          <CourseAssignSelect
            guideId={guide.id}
            currentCourseId={guide.course_id}
            onCourseChanged={(courseId) => setGuide({ ...guide, course_id: courseId })}
          />
          <button className="print-btn" onClick={() => window.print()}>Print</button>
          <button
            className="print-btn"
            onClick={async () => {
              try {
                const result = await studyApi.generateGuide({
                  title: guide.title.replace(/^Study Guide: /, ''),
                  content: guide.content,
                  regenerate_from_id: guide.id,
                });
                navigate(`/study/guide/${result.id}`);
              } catch {
                setError('Failed to regenerate');
              }
            }}
          >
            Regenerate
          </button>
          <button className="delete-btn" onClick={handleDelete}>Delete</button>
        </div>
      </div>

      <div className="study-guide-content">
        <h1>{guide.title}</h1>
        <p className="guide-meta">
          {guide.version > 1 && <span style={{ background: '#e3f2fd', color: '#1565c0', padding: '1px 6px', borderRadius: '8px', fontSize: '0.85rem', marginRight: '0.5rem' }}>v{guide.version}</span>}
          Created: {new Date(guide.created_at).toLocaleDateString()}
        </p>
        <div className="guide-body">
          {renderGuideContent(guide.content)}
        </div>
      </div>
    </div>
  );
}
